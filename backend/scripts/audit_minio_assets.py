from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import socket
import sys
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from backend.core.database import get_conn, init_db
from backend.core.storage import (
    get_primary_pdf_asset,
    object_asset_exists,
    object_storage_enabled,
    resolve_local_pdf_path,
)


def _can_reach_object_storage(timeout_seconds: float = 0.5) -> bool:
    if not object_storage_enabled():
        return False
    import os

    raw = os.getenv("MINIO_ENDPOINT", "").strip()
    if not raw:
        return False
    if ":" in raw:
        host, port_raw = raw.rsplit(":", 1)
        try:
            port = int(port_raw)
        except ValueError:
            return False
    else:
        host = raw
        port = 443 if str(os.getenv("MINIO_SECURE", "")).strip().lower() in {"1", "true", "yes", "on"} else 80
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _load_papers(selected_ids: Optional[List[int]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    query = """
        SELECT id, title, source_url, pdf_path
        FROM papers
        ORDER BY id ASC
    """
    params: tuple[Any, ...] = ()
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        query = query.replace("ORDER BY id ASC", f"WHERE id IN ({placeholders}) ORDER BY id ASC")
        params = tuple(selected_ids)
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _classify_storage_state(
    *,
    local_exists: bool,
    has_primary_asset: bool,
    object_exists: Optional[bool],
) -> Tuple[str, List[str]]:
    issues: List[str] = []
    if not has_primary_asset:
        issues.append("missing_primary_asset")
    if not local_exists:
        issues.append("missing_local_pdf")
    if has_primary_asset and object_exists is False:
        issues.append("missing_minio_object")
    if has_primary_asset and object_exists is None:
        issues.append("minio_object_unverified")

    if has_primary_asset and object_exists is False:
        return "broken", issues
    if local_exists and has_primary_asset:
        return "minio_backed", issues
    if (not local_exists) and has_primary_asset:
        return "minio_only", issues
    if local_exists and (not has_primary_asset):
        return "local_only", issues
    return "broken", issues


def _audit_paper(row: Dict[str, Any], *, object_checks_enabled: bool) -> Dict[str, Any]:
    paper_id = int(row["id"])
    raw_pdf_path = row.get("pdf_path")
    local_path = resolve_local_pdf_path(raw_pdf_path)
    local_exists = local_path is not None
    asset = get_primary_pdf_asset(paper_id)
    object_exists: Optional[bool] = None
    object_check_error: Optional[str] = None
    if asset is not None and object_checks_enabled:
        try:
            object_exists = object_asset_exists(asset)
        except Exception as exc:
            object_check_error = str(exc)
    status, issues = _classify_storage_state(
        local_exists=local_exists,
        has_primary_asset=asset is not None,
        object_exists=object_exists,
    )
    if object_check_error:
        issues.append("object_check_error")
    if asset is not None and not object_checks_enabled:
        issues.append("object_check_unavailable")
    return {
        "paper_id": paper_id,
        "title": row.get("title"),
        "source_url": row.get("source_url"),
        "raw_pdf_path": raw_pdf_path,
        "resolved_local_pdf_path": str(local_path) if local_path is not None else None,
        "local_exists": local_exists,
        "has_primary_asset": asset is not None,
        "object_storage_enabled": object_storage_enabled(),
        "object_exists": object_exists,
        "object_check_error": object_check_error,
        "status": status,
        "issues": issues,
        "asset": {
            "id": asset.get("id"),
            "storage_backend": asset.get("storage_backend"),
            "bucket": asset.get("bucket"),
            "object_key": asset.get("object_key"),
            "version_id": asset.get("version_id"),
            "source_kind": asset.get("source_kind"),
            "original_filename": asset.get("original_filename"),
            "is_primary": asset.get("is_primary"),
        }
        if asset is not None
        else None,
    }


def _render_text_report(report: Dict[str, Any]) -> str:
    lines = [
        f"papers: {report['total_papers']}",
        f"object_storage_enabled: {report['object_storage_enabled']}",
        "",
        "status_counts:",
    ]
    for key, value in sorted(report["status_counts"].items()):
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("issue_counts:")
    for key, value in sorted(report["issue_counts"].items()):
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("papers:")
    for item in report["papers"]:
        issue_text = ",".join(item["issues"]) if item["issues"] else "-"
        lines.append(
            f"  {item['paper_id']}: {item['status']} | local={item['local_exists']} "
            f"| asset={item['has_primary_asset']} | object={item['object_exists']} | issues={issue_text} | {item['title']}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit MinIO-backed paper asset health.")
    parser.add_argument(
        "--paper-id",
        action="append",
        type=int,
        dest="paper_ids",
        help="Only audit the given paper ID. Repeatable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only inspect the first N papers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a text report.",
    )
    args = parser.parse_args()

    init_db()
    object_checks_enabled = _can_reach_object_storage()
    papers = _load_papers(args.paper_ids, args.limit)
    audited = [_audit_paper(row, object_checks_enabled=object_checks_enabled) for row in papers]

    status_counts = Counter(item["status"] for item in audited)
    issue_counts = Counter(issue for item in audited for issue in item["issues"])
    report = {
        "total_papers": len(audited),
        "object_storage_enabled": object_storage_enabled(),
        "object_checks_enabled": object_checks_enabled,
        "status_counts": dict(status_counts),
        "issue_counts": dict(issue_counts),
        "papers": audited,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_text_report(report))


if __name__ == "__main__":
    main()
