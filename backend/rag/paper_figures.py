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

from ia_phase1.figures import (  # noqa: E402
    extract_and_store_paper_figures as _extract_and_store_paper_figures_impl,
    load_paper_figure_manifest as _load_paper_figure_manifest_impl,
    resolve_figure_file as _resolve_figure_file_impl,
)
from backend.core.storage import load_json_paper_asset  # noqa: E402


def extract_and_store_paper_figures(*args, **kwargs):
    return _extract_and_store_paper_figures_impl(*args, **kwargs)


def load_paper_figure_manifest(paper_id: int):
    payload = _load_paper_figure_manifest_impl(paper_id)
    images = payload.get("images") if isinstance(payload, dict) else None
    if isinstance(images, list) and images:
        return payload
    fallback = load_json_paper_asset(paper_id, role="figure_manifest")
    if fallback is not None:
        return fallback
    return payload


def resolve_figure_file(paper_id: int, figure_name: str):
    return _resolve_figure_file_impl(paper_id, figure_name)

__all__ = [
    "extract_and_store_paper_figures",
    "load_paper_figure_manifest",
    "resolve_figure_file",
]
