from __future__ import annotations

"""
Compatibility wrapper for table extraction utilities.

Backend code now delegates to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.tables import (  # noqa: E402
    extract_and_store_paper_tables as _extract_and_store_paper_tables_impl,
    load_paper_table_manifest as _load_paper_table_manifest_impl,
    table_records_to_chunks,
)
from backend.core.storage import load_json_paper_asset  # noqa: E402


def extract_and_store_paper_tables(*args, **kwargs):
    return _extract_and_store_paper_tables_impl(*args, **kwargs)


def load_paper_table_manifest(paper_id: int):
    payload = _load_paper_table_manifest_impl(paper_id)
    tables = payload.get("tables") if isinstance(payload, dict) else None
    if isinstance(tables, list) and tables:
        return payload
    fallback = load_json_paper_asset(paper_id, role="table_manifest")
    if fallback is not None:
        return fallback
    return payload

__all__ = [
    "extract_and_store_paper_tables",
    "table_records_to_chunks",
    "load_paper_table_manifest",
]
