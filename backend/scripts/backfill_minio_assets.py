from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from backend.core.database import get_conn, init_db
from backend.core.storage import object_storage_enabled, paper_ids_with_primary_pdf_assets, upload_primary_pdf_asset


def _infer_source_kind(row: Dict[str, Any]) -> str:
    source_url = str(row.get("source_url") or "").strip().lower()
    pdf_path = str(row.get("pdf_path") or "").strip()
    if source_url.startswith("http://") or source_url.startswith("https://"):
        if "arxiv.org" in source_url:
            return "arxiv_pdf"
        return "remote_pdf"
    if pdf_path:
        return "local_pdf"
    return "backfill_pdf"


def _load_candidates(selected_ids: List[int] | None = None) -> List[Dict[str, Any]]:
    query = """
        SELECT id, title, source_url, pdf_path
        FROM papers
        WHERE COALESCE(pdf_path, '') != ''
    """
    params: tuple[Any, ...] = ()
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        query += f" AND id IN ({placeholders})"
        params = tuple(selected_ids)
    query += " ORDER BY id ASC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload existing local PDF library papers into MinIO-backed paper_assets.")
    parser.add_argument(
        "--paper-id",
        action="append",
        type=int,
        dest="paper_ids",
        help="Only backfill the given paper ID. Repeatable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N candidate papers.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Upload even if the paper already has a primary PDF asset.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without modifying MinIO or SQLite asset rows.",
    )
    args = parser.parse_args()

    init_db()
    if not object_storage_enabled():
        raise SystemExit("Object storage is not configured. Set MINIO_* variables in backend/.env first.")

    candidates = _load_candidates(args.paper_ids)
    existing_assets = paper_ids_with_primary_pdf_assets(int(row["id"]) for row in candidates)

    uploaded = 0
    skipped_existing = 0
    skipped_missing = 0
    skipped_invalid = 0
    errors: List[Dict[str, Any]] = []
    processed: List[Dict[str, Any]] = []

    for row in candidates:
        paper_id = int(row["id"])
        pdf_path = Path(str(row["pdf_path"])).expanduser()

        if args.limit is not None and len(processed) >= args.limit:
            break

        if not args.force and paper_id in existing_assets:
            skipped_existing += 1
            continue

        if not pdf_path.exists():
            skipped_missing += 1
            errors.append(
                {
                    "paper_id": paper_id,
                    "title": row.get("title"),
                    "error": f"missing_file:{pdf_path}",
                }
            )
            continue

        if pdf_path.suffix.lower() != ".pdf":
            skipped_invalid += 1
            errors.append(
                {
                    "paper_id": paper_id,
                    "title": row.get("title"),
                    "error": f"non_pdf_path:{pdf_path}",
                }
            )
            continue

        processed.append(
            {
                "paper_id": paper_id,
                "title": row.get("title"),
                "pdf_path": str(pdf_path),
            }
        )

        if args.dry_run:
            continue

        try:
            upload_primary_pdf_asset(
                paper_id,
                pdf_path,
                source_kind=_infer_source_kind(row),
                original_filename=pdf_path.name,
            )
            uploaded += 1
        except Exception as exc:
            errors.append(
                {
                    "paper_id": paper_id,
                    "title": row.get("title"),
                    "error": str(exc),
                }
            )

    print(
        json.dumps(
            {
                "candidates": len(candidates),
                "processed": len(processed),
                "uploaded": uploaded,
                "skipped_existing": skipped_existing,
                "skipped_missing": skipped_missing,
                "skipped_invalid": skipped_invalid,
                "dry_run": bool(args.dry_run),
                "forced": bool(args.force),
                "errors": errors,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
