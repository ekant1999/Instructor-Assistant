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
    extract_and_store_paper_equations as _extract_and_store_paper_equations_impl,
    load_paper_equation_manifest as _load_paper_equation_manifest_impl,
    resolve_equation_file as _resolve_equation_file_impl,
)
from backend.core.storage import load_json_paper_asset  # noqa: E402


def extract_and_store_paper_equations(*args, **kwargs):
    return _extract_and_store_paper_equations_impl(*args, **kwargs)


def load_paper_equation_manifest(paper_id: int):
    payload = _load_paper_equation_manifest_impl(paper_id)
    equations = payload.get("equations") if isinstance(payload, dict) else None
    if isinstance(equations, list) and equations:
        return payload
    fallback = load_json_paper_asset(paper_id, role="equation_manifest")
    if fallback is not None:
        return fallback
    return payload


def resolve_equation_file(paper_id: int, file_name: str):
    return _resolve_equation_file_impl(paper_id, file_name)

__all__ = [
    "extract_and_store_paper_equations",
    "equation_records_to_chunks",
    "load_paper_equation_manifest",
    "resolve_equation_file",
]
