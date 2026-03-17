from __future__ import annotations

"""
Compatibility wrapper for unified search pipeline helpers.

Backend code delegates search scoring/gating/aggregation logic to the reusable
Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.search_pipeline import (  # noqa: E402
    aggregate_section_hits_to_papers,
    annotate_hit_query_support,
    configure_connection_factory,
    filter_aggregated_papers_for_query,
    filter_section_hits_for_query,
    infer_localization_query_profile,
    infer_localization_section_role,
    infer_search_section_bucket,
    inject_title_only_candidates,
    localization_score_for_hit,
    merge_section_hits,
    paper_passes_search_gate,
    paper_title_bonus_lookup,
    query_token_stats,
    rerank_section_hits_for_localization,
    rrf_score,
    search_paper_sections_for_localization,
    search_section_hits_unified,
    section_bucket_multiplier,
    section_passes_search_gate,
    token_overlap,
)

try:  # noqa: E402
    from backend.core.database import get_conn
except ImportError:  # noqa: E402
    from core.database import get_conn

configure_connection_factory(get_conn)

__all__ = [
    "rrf_score",
    "token_overlap",
    "infer_search_section_bucket",
    "section_bucket_multiplier",
    "query_token_stats",
    "infer_localization_query_profile",
    "infer_localization_section_role",
    "paper_title_bonus_lookup",
    "annotate_hit_query_support",
    "localization_score_for_hit",
    "rerank_section_hits_for_localization",
    "search_paper_sections_for_localization",
    "section_passes_search_gate",
    "filter_section_hits_for_query",
    "paper_passes_search_gate",
    "filter_aggregated_papers_for_query",
    "inject_title_only_candidates",
    "merge_section_hits",
    "search_section_hits_unified",
    "aggregate_section_hits_to_papers",
]
