"""
Phase 1 reusable ingestion modules.

Modules:
- parser: resolve URLs/DOIs to PDFs and extract PDF text blocks.
- sectioning: annotate PDF blocks with canonical section metadata.
- chunking: build embedding-ready text chunks from blocks.
- tables: extract structured tables and convert them to table chunks.
- figures: extract embedded/vector figures with section mapping.
"""

from .chunking import chunk_text_blocks, simple_chunk_blocks
from .figures import (
    extract_and_store_paper_figures,
    load_paper_figure_manifest,
    resolve_figure_file,
)
from .parser import extract_pages, extract_text_blocks, resolve_any_to_pdf
from .sectioning import annotate_blocks_with_sections, canonicalize_heading
from .tables import (
    extract_and_store_paper_tables,
    load_paper_table_manifest,
    table_records_to_chunks,
)

__all__ = [
    "resolve_any_to_pdf",
    "extract_pages",
    "extract_text_blocks",
    "annotate_blocks_with_sections",
    "canonicalize_heading",
    "chunk_text_blocks",
    "simple_chunk_blocks",
    "extract_and_store_paper_tables",
    "load_paper_table_manifest",
    "table_records_to_chunks",
    "extract_and_store_paper_figures",
    "load_paper_figure_manifest",
    "resolve_figure_file",
]

__version__ = "0.1.0"
