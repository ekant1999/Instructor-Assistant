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

from ia_phase1.tables import (
    extract_and_store_paper_tables,
    load_paper_table_manifest,
    table_records_to_chunks,
)

__all__ = [
    "extract_and_store_paper_tables",
    "table_records_to_chunks",
    "load_paper_table_manifest",
]
