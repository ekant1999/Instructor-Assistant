"""
Phase 1 reusable ingestion modules.

Modules:
- parser: resolve URLs/DOIs to PDFs and extract PDF text blocks.
- sectioning: annotate PDF blocks with canonical section metadata.
- section_overview: generate section-wise overview paragraphs from annotated PDF blocks.
- chunking: build embedding-ready text chunks from blocks.
- tables: extract structured tables and convert them to table chunks.
- figures: extract embedded/vector figures with section mapping.
- equations: detect/display equations and convert them to equation chunks.
- equation_latex: text-to-LaTeX helpers for equation markdown output.
- math_markdown: reusable math/LaTeX delimiter normalization helpers.
- markdown_export: compose a structured markdown bundle with asset references.
- youtube_transcript: download and normalize YouTube subtitles to transcript text.
- search_keyword: SQLite FTS/LIKE search helpers.
- search_hybrid: pgvector + PostgreSQL FTS hybrid ranking helpers.
- search_context: section-match resolver utilities for hit localization/snippets.
- search_pipeline: unified search scoring, gating, merging, and paper aggregation helpers.
"""

from .chunking import chunk_text_blocks, simple_chunk_blocks
from .equations import (
    equation_records_to_chunks,
    extract_and_store_paper_equations,
    load_paper_equation_manifest,
    resolve_equation_file,
)
from .equation_latex import extract_equation_latex, fallback_text_to_latex, validate_equation_latex
from .figures import (
    extract_and_store_paper_figures,
    load_paper_figure_manifest,
    resolve_figure_file,
)
from .parser import describe_google_drive_source, extract_pages, extract_text_blocks, resolve_any_to_pdf
from .sectioning import annotate_blocks_with_sections, canonicalize_heading
from .section_overview import (
    SectionOverviewConfig,
    SectionOverviewItem,
    SectionOverviewResult,
    build_section_overview,
    render_section_overview_markdown,
)
from .search_context import (
    build_match_snippet,
    lexical_hits,
    pgvector_score,
    query_tokens,
    select_block_for_query,
)
from .search_pipeline import (
    aggregate_section_hits_to_papers,
    annotate_hit_query_support,
    configure_connection_factory as configure_search_pipeline_connection_factory,
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
    search_paper_sections_for_localization,
    rrf_score,
    search_section_hits_unified,
    section_bucket_multiplier,
    section_passes_search_gate,
    token_overlap,
)
from .search_hybrid import (
    full_text_search,
    hybrid_search,
    reciprocal_rank_fusion,
    search_with_reranking,
)
from .search_keyword import (
    SearchType,
    configure_connection_factory,
    search_all,
    search_notes,
    search_papers,
    search_sections,
    search_summaries,
)
from .tables import (
    extract_and_store_paper_tables,
    load_paper_table_manifest,
    resolve_table_file,
    table_records_to_chunks,
)
from .markdown_export import (
    MarkdownExportConfig,
    MarkdownExportResult,
    export_pdf_to_markdown,
    render_markdown_document,
)
from .math_markdown import normalize_math_delimiters
from .youtube_transcript import (
    download_youtube_transcript,
    extract_youtube_video_id,
    is_youtube_url,
)

__all__ = [
    "resolve_any_to_pdf",
    "describe_google_drive_source",
    "extract_pages",
    "extract_text_blocks",
    "annotate_blocks_with_sections",
    "canonicalize_heading",
    "SectionOverviewConfig",
    "SectionOverviewItem",
    "SectionOverviewResult",
    "build_section_overview",
    "render_section_overview_markdown",
    "chunk_text_blocks",
    "simple_chunk_blocks",
    "extract_and_store_paper_equations",
    "load_paper_equation_manifest",
    "equation_records_to_chunks",
    "resolve_equation_file",
    "extract_equation_latex",
    "fallback_text_to_latex",
    "validate_equation_latex",
    "extract_and_store_paper_tables",
    "load_paper_table_manifest",
    "resolve_table_file",
    "table_records_to_chunks",
    "extract_and_store_paper_figures",
    "load_paper_figure_manifest",
    "resolve_figure_file",
    "MarkdownExportConfig",
    "MarkdownExportResult",
    "export_pdf_to_markdown",
    "render_markdown_document",
    "normalize_math_delimiters",
    "SearchType",
    "configure_connection_factory",
    "search_papers",
    "search_sections",
    "search_notes",
    "search_summaries",
    "search_all",
    "full_text_search",
    "reciprocal_rank_fusion",
    "hybrid_search",
    "search_with_reranking",
    "query_tokens",
    "lexical_hits",
    "pgvector_score",
    "select_block_for_query",
    "build_match_snippet",
    "configure_search_pipeline_connection_factory",
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
    "extract_youtube_video_id",
    "is_youtube_url",
    "download_youtube_transcript",
]

__version__ = "0.1.0"
