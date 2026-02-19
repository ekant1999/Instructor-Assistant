"""
Regression tests for backend -> ia_phase1 modular wiring.
"""
from __future__ import annotations

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def test_backend_wrappers_delegate_to_ia_phase1() -> None:
    from core import pdf
    from rag import chunking, section_extractor, table_extractor, paper_figures

    assert pdf.extract_text_blocks.__module__ == "ia_phase1.parser"
    assert pdf.resolve_any_to_pdf.__module__ == "ia_phase1.parser"
    assert chunking.chunk_text_blocks.__module__ == "ia_phase1.chunking"
    assert section_extractor.annotate_blocks_with_sections.__module__ == "ia_phase1.sectioning"
    assert table_extractor.extract_and_store_paper_tables.__module__ == "ia_phase1.tables"
    assert paper_figures.extract_and_store_paper_figures.__module__ == "ia_phase1.figures"


def test_pgvector_insert_index_remap_prevents_collisions() -> None:
    from rag.pgvector_store import _ensure_unique_page_block_indices

    blocks = [
        {"page_no": 1, "block_index": 0, "text": "a", "metadata": {}},
        {"page_no": 1, "block_index": 0, "text": "b", "metadata": {"k": "v"}},
        {"page_no": 1, "block_index": 0, "text": "c", "metadata": {}},
        {"page_no": 2, "block_index": 5, "text": "x", "metadata": {}},
        {"page_no": 2, "block_index": 5, "text": "y", "metadata": {}},
    ]
    original = [(int(item["page_no"]), int(item["block_index"])) for item in blocks]

    rewrites = _ensure_unique_page_block_indices(blocks)

    assert rewrites == 3
    keys = [(int(item["page_no"]), int(item["block_index"])) for item in blocks]
    assert len(keys) == len(set(keys))
    assert blocks[0]["block_index"] == 0
    assert blocks[3]["block_index"] == 5

    for idx, block in enumerate(blocks):
        current = (int(block["page_no"]), int(block["block_index"]))
        if current != original[idx]:
            metadata = block.get("metadata") or {}
            assert metadata.get("source_block_index") == original[idx][1]
            assert metadata.get("source_page_no") == original[idx][0]
