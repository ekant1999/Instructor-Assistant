from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from ia_phase1.equations import (
    equation_records_to_chunks,
    extract_and_store_paper_equations,
    load_paper_equation_manifest,
)
from ia_phase1.parser import extract_text_blocks


def _build_equation_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "3 Problem Definition")
    page.insert_text((72, 98), "We define one-shot and sequential planning.")
    page.insert_text((180, 170), "P_i = {")
    page.insert_text((200, 194), "P_0, if i = 0")
    page.insert_text((200, 218), "compose(P_(i-1), U_i), if i >= 1")
    page.insert_text((180, 242), "} (1)")
    doc.save(str(path))
    doc.close()
    return path


def test_extract_and_store_paper_equations_detects_equation_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = _build_equation_pdf(tmp_path / "equation-sample.pdf")
    blocks = extract_text_blocks(pdf_path)
    for block in blocks:
        metadata = block.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            block["metadata"] = metadata
        metadata.setdefault("section_canonical", "problem_definition")
        metadata.setdefault("section_title", "Problem Definition")
        metadata.setdefault("section_source", "heuristic")
        metadata.setdefault("section_confidence", 0.8)

    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setenv("EQUATION_EXTRACTION_ENABLED", "true")
    monkeypatch.setenv("EQUATION_DETECTION_MIN_SCORE", "4.0")

    payload = extract_and_store_paper_equations(pdf_path, paper_id=19, blocks=blocks)

    assert payload["num_equations"] >= 1
    assert payload["manifest_path"]
    manifest = load_paper_equation_manifest(19)
    assert manifest["num_equations"] >= 1
    first = manifest["equations"][0]
    assert first["section_canonical"] == "problem_definition"
    if first.get("file_name"):
        assert (Path(tmp_path / "equations" / "19" / first["file_name"])).exists()


def test_equation_records_to_chunks_builds_metadata(sectioned_blocks) -> None:
    equations = [
        {
            "id": 4,
            "page_no": 2,
            "equation_number": "3",
            "text": "f(x) = x^2 + 1",
            "bbox": {"x0": 90, "y0": 140, "x1": 300, "y1": 180},
            "section_canonical": "methodology",
            "section_title": "Method",
            "section_source": "pdf_toc",
            "section_confidence": 0.93,
            "file_name": "equation_0004.png",
            "url": "/api/papers/42/equations/equation_0004.png",
            "detection_score": 6.2,
            "detection_flags": ["equation_number", "has_equals"],
        }
    ]
    chunks = equation_records_to_chunks(equations=equations, text_blocks=sectioned_blocks)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert "Equation 3" in chunk["text"]
    assert chunk["metadata"]["content_type"] == "equation"
    assert chunk["metadata"]["section_primary"] == "methodology"
    assert chunk["metadata"]["equation_id"] == 4


def test_load_paper_equation_manifest_returns_empty_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    payload = load_paper_equation_manifest(999)
    assert payload["num_equations"] == 0
    assert payload["equations"] == []

