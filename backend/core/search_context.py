from __future__ import annotations

"""
Compatibility wrapper for search context helpers.

Backend code delegates hit localization/snippet logic to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.search_context import (  # noqa: E402
    build_match_snippet,
    lexical_hits,
    pgvector_score,
    query_tokens,
    select_block_for_query,
)

__all__ = [
    "query_tokens",
    "lexical_hits",
    "pgvector_score",
    "select_block_for_query",
    "build_match_snippet",
]
