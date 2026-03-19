from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from backend.core.database import DATA_DIR, get_conn, init_db
from backend.core.storage import (
    get_primary_pdf_asset,
    object_asset_exists,
    object_storage_enabled,
    resolve_local_pdf_path,
    restore_primary_pdf_to_path,
    upload_primary_pdf_asset,
)


def _can_reach_object_storage(timeout_seconds: float = 0.5) -> bool:
    if not object_storage_enabled():
        return False
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


def _infer_source_kind(row: Dict[str, Any]) -> str:
    source_url = str(row.get("source_url") or "").strip().lower()
    pdf_path = str(row.get("pdf_path") or "").strip()
    if source_url.startswith("http://") or source_url.startswith("https://"):
        if "arxiv.org" in source_url:
            return "arxiv_pdf"
        if "docs.google.com" in source_url or "drive.google.com" in source_url:
            return "gdrive_pdf"
        return "remote_pdf"
    if pdf_path:
        return "local_pdf"
    return "repair_pdf"


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


def _desired_restore_path(row: Dict[str, Any], asset: Optional[Dict[str, Any]]) -> Path:
    raw_pdf_path = str(row.get("pdf_path") or "").strip()
    if raw_pdf_path:
        return Path(raw_pdf_path).expanduser()

    filename = None
    if asset is not None:
        filename = asset.get("original_filename")
    if not filename:
        filename = f"paper-{int(row['id'])}.pdf"
    return (DATA_DIR / "pdfs" / str(filename)).resolve()


def _set_paper_pdf_path(paper_id: int, path: Path) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE papers SET pdf_path = ? WHERE id = ?", (str(path), int(paper_id)))
        conn.commit()


def _repair_paper(
    row: Dict[str, Any],
    *,
    repair_local_cache: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    paper_id = int(row["id"])
    local_path = resolve_local_pdf_path(row.get("pdf_path"))
    asset = get_primary_pdf_asset(paper_id)
    object_exists: Optional[bool] = None
    if asset is not None:
        object_exists = object_asset_exists(asset)

    actions: List[Dict[str, Any]] = []
    errors: List[str] = []

    if asset is None and local_path is not None:
        actions.append(
            {
                "action": "upload_primary_asset",
                "source_path": str(local_path),
            }
        )
        if not dry_run:
            try:
                upload_primary_pdf_asset(
                    paper_id,
                    local_path,
                    source_kind=_infer_source_kind(row),
                    original_filename=local_path.name,
                )
            except Exception as exc:
                errors.append(str(exc))

    elif asset is not None and object_exists is False and local_path is not None:
        actions.append(
            {
                "action": "reupload_missing_object",
                "source_path": str(local_path),
                "stale_asset_id": asset.get("id"),
            }
        )
        if not dry_run:
            try:
                upload_primary_pdf_asset(
                    paper_id,
                    local_path,
                    source_kind=str(asset.get("source_kind") or _infer_source_kind(row)),
                    original_filename=str(asset.get("original_filename") or local_path.name),
                    external_file_id=asset.get("external_file_id"),
                    external_revision=asset.get("external_revision"),
                )
            except Exception as exc:
                errors.append(str(exc))

    elif asset is not None and local_path is None and object_exists is True and repair_local_cache:
        restore_path = _desired_restore_path(row, asset)
        actions.append(
            {
                "action": "restore_local_cache",
                "destination_path": str(restore_path),
            }
        )
        if not dry_run:
            try:
                restored_path = restore_primary_pdf_to_path(paper_id, restore_path)
                _set_paper_pdf_path(paper_id, restored_path)
            except Exception as exc:
                errors.append(str(exc))

    elif asset is None and local_path is None:
        errors.append("unrecoverable:no_local_pdf_and_no_primary_asset")
    elif asset is not None and object_exists is False and local_path is None:
        errors.append("unrecoverable:missing_minio_object_and_no_local_pdf")

    return {
        "paper_id": paper_id,
        "title": row.get("title"),
        "actions": actions,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair recoverable MinIO-backed paper asset issues.")
    parser.add_argument(
        "--paper-id",
        action="append",
        type=int,
        dest="paper_ids",
        help="Only repair the given paper ID. Repeatable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only inspect the first N papers.",
    )
    parser.add_argument(
        "--repair-local-cache",
        action="store_true",
        help="Restore missing local PDF files from MinIO when a valid primary asset exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned repairs without modifying SQLite, MinIO, or local files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of pretty-printed JSON.",
    )
    args = parser.parse_args()

    init_db()
    if not object_storage_enabled():
        raise SystemExit("Object storage is not configured. Set MINIO_* variables in backend/.env first.")
    if not _can_reach_object_storage():
        raise SystemExit("Object storage is not reachable. Start MinIO first, then rerun this repair script.")

    rows = _load_papers(args.paper_ids, args.limit)
    results = [
        _repair_paper(
            row,
            repair_local_cache=bool(args.repair_local_cache),
            dry_run=bool(args.dry_run),
        )
        for row in rows
    ]

    report = {
        "papers": len(rows),
        "dry_run": bool(args.dry_run),
        "repair_local_cache": bool(args.repair_local_cache),
        "papers_with_actions": sum(1 for item in results if item["actions"]),
        "actions_planned_or_applied": sum(len(item["actions"]) for item in results),
        "papers_with_errors": sum(1 for item in results if item["errors"]),
        "results": results,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
