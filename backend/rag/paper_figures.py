from __future__ import annotations

"""
Compatibility wrapper for figure extraction utilities.

Backend code now delegates to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.figures import (
    extract_and_store_paper_figures,
    load_paper_figure_manifest,
    resolve_figure_file,
)

__all__ = [
    "extract_and_store_paper_figures",
    "load_paper_figure_manifest",
    "resolve_figure_file",
]
