from __future__ import annotations

from pathlib import Path

import pytest

from ia_phase1.chunking import chunk_text_blocks
from ia_phase1.figures import extract_and_store_paper_figures
from ia_phase1.parser import extract_text_blocks
from ia_phase1.sectioning import annotate_blocks_with_sections
from ia_phase1.tables import extract_and_store_paper_tables


@pytest.mark.integration
def test_end_to_end_phase1_contract(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("TABLE_EXTRACTION_ENABLED", "false")
    monkeypatch.setenv("FIGURE_VECTOR_ENABLED", "false")

    blocks = extract_text_blocks(sample_pdf)
    section_report = annotate_blocks_with_sections(
        blocks=blocks,
        pdf_path=sample_pdf,
        source_url="https://arxiv.org/abs/2501.00001",
    )
    chunks = chunk_text_blocks(blocks, target_size=220, overlap=40, min_chunk_size=50)
    table_report = extract_and_store_paper_tables(sample_pdf, paper_id=901, blocks=blocks)
    figure_report = extract_and_store_paper_figures(sample_pdf, paper_id=901, blocks=blocks)

    assert len(blocks) > 0
    assert len(chunks) > 0
    assert "strategy" in section_report
    assert table_report["num_tables"] == 0
    assert figure_report["num_images"] == 0
