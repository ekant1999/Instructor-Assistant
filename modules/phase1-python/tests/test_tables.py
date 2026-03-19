from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from ia_phase1.tables import (
    extract_and_store_paper_tables,
    load_paper_table_manifest,
    table_records_to_chunks,
)


def test_extract_tables_returns_empty_when_disabled(
    sample_pdf: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_EXTRACTION_ENABLED", "false")
    payload = extract_and_store_paper_tables(sample_pdf, paper_id=77, blocks=[])
    assert payload["paper_id"] == 77
    assert payload["num_tables"] == 0
    assert payload["tables"] == []


def test_table_records_to_chunks_builds_table_metadata() -> None:
    tables = [
        {
            "id": 1,
            "page_no": 2,
            "caption": "Table 1: Results",
            "n_rows": 2,
            "n_cols": 3,
            "headers": ["Model", "PSNR", "SSIM"],
            "rows": [["A", "30.1", "0.92"], ["B", "31.2", "0.94"]],
            "bbox": {"x0": 10, "y0": 10, "x1": 400, "y1": 200},
            "section_canonical": "experiments",
            "section_title": "Experiments",
            "section_source": "pdf_toc",
            "section_confidence": 0.97,
        }
    ]
    text_blocks = [{"page_no": 2, "block_index": 4, "text": "context", "bbox": None, "metadata": {}}]
    chunks = table_records_to_chunks(tables=tables, text_blocks=text_blocks)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert "Table 1: Results" in chunk["text"]
    assert chunk["metadata"]["content_type"] == "table"
    assert chunk["metadata"]["section_primary"] == "experiments"
    assert chunk["metadata"]["table_total_cols"] == 3


def test_load_table_manifest_missing_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path))
    payload = load_paper_table_manifest(9999)
    assert payload["paper_id"] == 9999
    assert payload["num_tables"] == 0
    assert payload["tables"] == []


def test_load_table_manifest_reads_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path))
    paper_dir = tmp_path / "12"
    paper_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "paper_id": 12,
        "num_tables": 1,
        "tables": [{"id": 1, "caption": "Table 1"}],
    }
    (paper_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    payload = load_paper_table_manifest(12)
    assert payload["paper_id"] == 12
    assert payload["num_tables"] == 1
    assert payload["tables"][0]["id"] == 1


def _build_ruled_table_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 56), "Table 1. Example results")
    x0, y0 = 72, 88
    width, height = 240, 96
    rows, cols = 3, 3
    for row_idx in range(rows + 1):
        y = y0 + (row_idx * height / rows)
        page.draw_line((x0, y), (x0 + width, y))
    for col_idx in range(cols + 1):
        x = x0 + (col_idx * width / cols)
        page.draw_line((x, y0), (x, y0 + height))

    labels = [["Model", "PSNR", "SSIM"], ["A", "30.1", "0.92"], ["B", "31.2", "0.94"]]
    for row_idx, row in enumerate(labels):
        for col_idx, text in enumerate(row):
            page.insert_text((x0 + 10 + col_idx * width / cols, y0 + 18 + row_idx * height / rows), text)
    doc.save(str(path))
    doc.close()


def _build_caption_plus_prose_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((72, 72, 500, 100), "Table 1. Performance comparison across models.", fontsize=12)
    prose = ("This paragraph discusses the results in prose and should not be extracted as a table. " * 8).strip()
    page.insert_textbox((72, 120, 520, 260), prose, fontsize=11)
    doc.save(str(path))
    doc.close()


def test_extract_tables_uses_native_pymupdf_detection_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "ruled_table.pdf"
    _build_ruled_table_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.delenv("TABLE_TEXT_FALLBACK_ENABLED", raising=False)

    payload = extract_and_store_paper_tables(pdf_path, paper_id=88, blocks=[])

    assert payload["num_tables"] == 1
    table = payload["tables"][0]
    assert table["detection_strategy"] == "pymupdf_native"
    # Native PyMuPDF markdown omits the padded cells our fallback renderer adds.
    assert table["markdown"].startswith("|Model|PSNR|SSIM|")


def test_extract_tables_does_not_promote_caption_plus_prose_to_table_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "caption_prose.pdf"
    _build_caption_plus_prose_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.delenv("TABLE_TEXT_FALLBACK_ENABLED", raising=False)

    payload = extract_and_store_paper_tables(pdf_path, paper_id=89, blocks=[])

    assert payload["num_tables"] == 0


def test_extract_tables_text_fallback_remains_opt_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "caption_prose_opt_in.pdf"
    _build_caption_plus_prose_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("TABLE_TEXT_FALLBACK_ENABLED", "true")

    payload = extract_and_store_paper_tables(pdf_path, paper_id=90, blocks=[])

    assert payload["num_tables"] == 1
    assert payload["tables"][0]["detection_strategy"] == "text_caption_fallback"
