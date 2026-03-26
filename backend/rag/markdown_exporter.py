from __future__ import annotations

"""
Compatibility wrapper for markdown export utilities.

Backend code delegates to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.markdown_export import (  # noqa: E402
    MarkdownExportConfig,
    MarkdownExportResult,
    export_pdf_to_markdown,
    render_markdown_document,
)

__all__ = [
    "MarkdownExportConfig",
    "MarkdownExportResult",
    "export_pdf_to_markdown",
    "render_markdown_document",
]
