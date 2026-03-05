"""
Phase 1 reusable ingestion modules.

Modules:
- parser: resolve URLs/DOIs to PDFs and extract PDF text blocks.
- sectioning: annotate PDF blocks with canonical section metadata.
- chunking: build embedding-ready text chunks from blocks.
- tables: extract structured tables and convert them to table chunks.
- figures: extract embedded/vector figures with section mapping.
- equations: detect/display equations and convert them to equation chunks.
- youtube_transcript: download and normalize YouTube subtitles to transcript text.
- search_keyword: SQLite FTS/LIKE search helpers.
- search_hybrid: pgvector + PostgreSQL FTS hybrid ranking helpers.
- search_context: section-match resolver utilities for hit localization/snippets.
"""

from .chunking import chunk_text_blocks, simple_chunk_blocks
from .equations import (
    equation_records_to_chunks,
    extract_and_store_paper_equations,
    load_paper_equation_manifest,
    resolve_equation_file,
)
from .figures import (
    extract_and_store_paper_figures,
    load_paper_figure_manifest,
    resolve_figure_file,
)
from .parser import extract_pages, extract_text_blocks, resolve_any_to_pdf
from .sectioning import annotate_blocks_with_sections, canonicalize_heading
from .search_context import (
    build_match_snippet,
    lexical_hits,
    pgvector_score,
    query_tokens,
    select_block_for_query,
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
    table_records_to_chunks,
)
from .youtube_transcript import (
    download_youtube_transcript,
    extract_youtube_video_id,
    is_youtube_url,
)

__all__ = [
    "resolve_any_to_pdf",
    "extract_pages",
    "extract_text_blocks",
    "annotate_blocks_with_sections",
    "canonicalize_heading",
    "chunk_text_blocks",
    "simple_chunk_blocks",
    "extract_and_store_paper_equations",
    "load_paper_equation_manifest",
    "equation_records_to_chunks",
    "resolve_equation_file",
    "extract_and_store_paper_tables",
    "load_paper_table_manifest",
    "table_records_to_chunks",
    "extract_and_store_paper_figures",
    "load_paper_figure_manifest",
    "resolve_figure_file",
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
    "extract_youtube_video_id",
    "is_youtube_url",
    "download_youtube_transcript",
]

__version__ = "0.1.0"
