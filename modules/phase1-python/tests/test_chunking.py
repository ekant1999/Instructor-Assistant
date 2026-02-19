from __future__ import annotations

from typing import Dict, List

from ia_phase1.chunking import chunk_text_blocks, simple_chunk_blocks


def _block(
    text: str,
    page_no: int,
    block_index: int,
    section: str,
    title: str,
) -> Dict[str, object]:
    return {
        "text": text,
        "page_no": page_no,
        "block_index": block_index,
        "bbox": {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 30.0},
        "metadata": {
            "section_canonical": section,
            "section_title": title,
            "section_source": "heuristic",
            "section_confidence": 0.8,
        },
    }


def test_chunk_text_blocks_propagates_section_metadata() -> None:
    blocks: List[Dict[str, object]] = [
        _block("A" * 120, 1, 0, "abstract", "Abstract"),
        _block("B" * 120, 1, 1, "introduction", "Introduction"),
        _block("C" * 120, 2, 0, "methodology", "Method"),
    ]
    chunks = chunk_text_blocks(blocks, target_size=250, overlap=50, min_chunk_size=80)
    assert len(chunks) >= 2
    for chunk in chunks:
        metadata = chunk["metadata"]
        assert "section_primary" in metadata
        assert "section_all" in metadata
        assert "section_confidence" in metadata


def test_chunk_text_blocks_splits_very_large_block() -> None:
    blocks = [_block("X" * 3200, 1, 0, "introduction", "Introduction")]
    chunks = chunk_text_blocks(blocks, target_size=900, overlap=100, min_chunk_size=100)
    assert len(chunks) >= 3
    assert all(chunk["metadata"]["chunk_type"] == "split" for chunk in chunks)


def test_simple_chunk_blocks_combines_nearby_blocks() -> None:
    blocks = [
        _block("A" * 90, 1, 0, "abstract", "Abstract"),
        _block("B" * 90, 1, 1, "abstract", "Abstract"),
        _block("C" * 90, 1, 2, "introduction", "Introduction"),
    ]
    chunks = simple_chunk_blocks(blocks, max_chars=210)
    assert len(chunks) == 2
    assert "A" in chunks[0]["text"]
    assert "B" in chunks[0]["text"]
    assert "C" in chunks[1]["text"]
