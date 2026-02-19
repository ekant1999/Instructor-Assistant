from __future__ import annotations

import json
from pathlib import Path

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
