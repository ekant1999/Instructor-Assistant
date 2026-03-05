from __future__ import annotations

"""
Compatibility wrapper for equation extraction utilities.

Backend code delegates to reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.equations import (  # noqa: E402
    equation_records_to_chunks,
    extract_and_store_paper_equations,
    load_paper_equation_manifest,
    resolve_equation_file,
)

__all__ = [
    "extract_and_store_paper_equations",
    "equation_records_to_chunks",
    "load_paper_equation_manifest",
    "resolve_equation_file",
]

