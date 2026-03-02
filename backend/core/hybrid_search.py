from __future__ import annotations

"""
Compatibility wrapper for hybrid search helpers.

Backend code delegates fusion logic to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.search_hybrid import (  # noqa: E402
    full_text_search,
    hybrid_search,
    reciprocal_rank_fusion,
    search_with_reranking,
)

__all__ = [
    "full_text_search",
    "reciprocal_rank_fusion",
    "hybrid_search",
    "search_with_reranking",
]
