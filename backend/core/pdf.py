from __future__ import annotations

"""
Compatibility wrapper for PDF parsing utilities.

Backend code now delegates to the reusable Phase 1 package (`ia_phase1`).
"""

from .phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.parser import describe_google_drive_source, extract_pages, extract_text_blocks, resolve_any_to_pdf

__all__ = [
    "resolve_any_to_pdf",
    "describe_google_drive_source",
    "extract_pages",
    "extract_text_blocks",
]
