from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from ia_phase1.equations import (
    _merge_equation_candidates,
    equation_records_to_chunks,
    extract_and_store_paper_equations,
    load_paper_equation_manifest,
)
from ia_phase1.equation_latex import fallback_text_to_latex, validate_equation_latex
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


def _build_equation_with_leading_prose_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "1 Introduction")
    page.insert_text((72, 96), "Low-Rank Adaptation is the dominant method for parameter-efficient fine-tuning.")
    page.insert_text((72, 122), "DoRA extends LoRA by decomposing the adapted weight into magnitude")
    page.insert_text((72, 138), "and direction:")
    page.insert_text((240, 164), "W′ = m ⊙")
    page.insert_text((308, 178), "W + sBA")
    page.insert_text((296, 194), "∥W + sBA∥row")
    page.insert_text((527, 194), "(1)")
    page.insert_text((72, 228), "where W is the frozen base weight.")
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
    monkeypatch.setenv("EQUATION_LATEX_BACKEND", "text")

    payload = extract_and_store_paper_equations(pdf_path, paper_id=19, blocks=blocks)

    assert payload["num_equations"] >= 1
    assert payload["manifest_path"]
    manifest = load_paper_equation_manifest(19)
    assert manifest["num_equations"] >= 1
    first = manifest["equations"][0]
    assert first["section_canonical"] == "problem_definition"
    assert first["latex"]
    assert first["latex_source"] == "text_fallback"
    assert first["render_mode"] == "latex"
    if first.get("file_name"):
        assert (Path(tmp_path / "equations" / "19" / first["file_name"])).exists()


def test_extract_and_store_paper_equations_avoids_paragraph_bleed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = _build_equation_with_leading_prose_pdf(tmp_path / "equation-prose-sample.pdf")
    blocks = extract_text_blocks(pdf_path)
    for block in blocks:
        metadata = block.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            block["metadata"] = metadata
        metadata.setdefault("section_canonical", "introduction")
        metadata.setdefault("section_title", "Introduction")
        metadata.setdefault("section_source", "heuristic")
        metadata.setdefault("section_confidence", 0.8)

    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setenv("EQUATION_EXTRACTION_ENABLED", "true")
    monkeypatch.setenv("EQUATION_DETECTION_MIN_SCORE", "4.0")
    monkeypatch.setenv("EQUATION_LATEX_BACKEND", "text")

    payload = extract_and_store_paper_equations(pdf_path, paper_id=110, blocks=blocks)

    assert payload["num_equations"] >= 1
    manifest = load_paper_equation_manifest(110)
    first = manifest["equations"][0]
    assert "Low-Rank Adaptation" not in first["text"]
    assert "and direction:" not in first["text"]
    assert "=" in first["text"]
    assert "row" in first["text"]
    assert first["equation_number"] == "1"
    assert first["latex"]
    assert "\\tag{1}" in first["latex"]
    assert first["latex_source"] == "text_fallback"


def test_equation_records_to_chunks_builds_metadata(sectioned_blocks) -> None:
    equations = [
        {
            "id": 4,
            "page_no": 2,
            "equation_number": "3",
            "text": "f(x) = x^2 + 1",
            "latex": "f(x) = x^2 + 1",
            "latex_source": "text_fallback",
            "render_mode": "latex",
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
    assert "LaTeX: f(x) = x^2 + 1" in chunk["text"]
    assert chunk["metadata"]["content_type"] == "equation"
    assert chunk["metadata"]["section_primary"] == "methodology"
    assert chunk["metadata"]["equation_id"] == 4
    assert chunk["metadata"]["equation_latex"] == "f(x) = x^2 + 1"
    assert chunk["metadata"]["equation_render_mode"] == "latex"


def test_fallback_text_to_latex_builds_display_math() -> None:
    latex = fallback_text_to_latex("W′ = m ⊙\nW + s BA\n∥W + s BA∥row\n(1)", equation_number="1")

    assert latex is not None
    assert "\\odot" in latex
    assert "\\tag{1}" in latex
    valid, flags = validate_equation_latex(latex)
    assert valid, flags


def test_merge_equation_candidates_merges_fragmented_numbered_equation() -> None:
    candidates = [
        {
            "page_no": 1,
            "bbox": {"x0": 240.0, "y0": 100.0, "x1": 360.0, "y1": 120.0},
            "lines": ["x = y +"],
            "text": "x = y +",
            "score": 6.0,
            "flags": ["has_equals", "math_symbols"],
            "equation_number": None,
        },
        {
            "page_no": 1,
            "bbox": {"x0": 250.0, "y0": 124.0, "x1": 340.0, "y1": 142.0},
            "lines": ["z / w"],
            "text": "z / w",
            "score": 4.8,
            "flags": ["math_symbols"],
            "equation_number": None,
        },
        {
            "page_no": 1,
            "bbox": {"x0": 330.0, "y0": 146.0, "x1": 348.0, "y1": 160.0},
            "lines": ["(2)"],
            "text": "(2)",
            "score": 10.0,
            "flags": ["equation_number_only", "equation_number"],
            "equation_number": "2",
        },
    ]

    merged = _merge_equation_candidates(candidates)

    assert len(merged) == 1
    assert merged[0]["equation_number"] == "2"
    assert "x = y +" in merged[0]["text"]
    assert "z / w" in merged[0]["text"]
    assert "(2)" in merged[0]["text"]


def test_merge_equation_candidates_drops_orphan_number_only() -> None:
    merged = _merge_equation_candidates(
        [
            {
                "page_no": 1,
                "bbox": {"x0": 330.0, "y0": 146.0, "x1": 348.0, "y1": 160.0},
                "lines": ["(7)"],
                "text": "(7)",
                "score": 10.0,
                "flags": ["equation_number_only", "equation_number"],
                "equation_number": "7",
            }
        ]
    )

    assert merged == []


def test_merge_equation_candidates_merges_same_row_fragments() -> None:
    candidates = [
        {
            "page_no": 2,
            "bbox": {"x0": 160.0, "y0": 200.0, "x1": 280.0, "y1": 220.0},
            "lines": ["∥W + s BA∥2", "row = ∥W∥2"],
            "text": "∥W + s BA∥2\nrow = ∥W∥2",
            "score": 13.2,
            "flags": ["math_symbols", "has_equals"],
            "equation_number": None,
        },
        {
            "page_no": 2,
            "bbox": {"x0": 380.0, "y0": 200.0, "x1": 436.0, "y1": 220.0},
            "lines": ["+ s 2 ∥BA∥2"],
            "text": "+ s 2 ∥BA∥2",
            "score": 5.5,
            "flags": ["math_symbols"],
            "equation_number": None,
        },
        {
            "page_no": 2,
            "bbox": {"x0": 528.0, "y0": 201.0, "x1": 542.0, "y1": 217.0},
            "lines": ["(2)"],
            "text": "(2)",
            "score": 10.0,
            "flags": ["equation_number_only", "equation_number"],
            "equation_number": "2",
        },
    ]

    merged = _merge_equation_candidates(candidates)

    assert len(merged) == 1
    assert merged[0]["equation_number"] == "2"
    assert "∥W + s BA∥2" in merged[0]["text"]
    assert "+ s 2 ∥BA∥2" in merged[0]["text"]
    assert "(2)" in merged[0]["text"]


def test_merge_equation_candidates_keeps_distinct_numbers_separate() -> None:
    candidates = [
        {
            "page_no": 3,
            "bbox": {"x0": 250.0, "y0": 365.0, "x1": 433.0, "y1": 390.0},
            "lines": ["∥W∥2", "row + 2 s · cross + s 2 · ba_norm, 0", "(5)"],
            "text": "∥W∥2\nrow + 2 s · cross + s 2 · ba_norm, 0\n(5)",
            "score": 20.0,
            "flags": ["math_symbols", "equation_number"],
            "equation_number": "5",
        },
        {
            "page_no": 3,
            "bbox": {"x0": 170.0, "y0": 367.0, "x1": 212.0, "y1": 384.0},
            "lines": ["w norm ="],
            "text": "w norm =",
            "score": 6.1,
            "flags": ["has_equals"],
            "equation_number": None,
        },
        {
            "page_no": 3,
            "bbox": {"x0": 527.0, "y0": 416.0, "x1": 541.0, "y1": 432.0},
            "lines": ["(6)"],
            "text": "(6)",
            "score": 10.0,
            "flags": ["equation_number_only", "equation_number"],
            "equation_number": "6",
        },
    ]

    merged = _merge_equation_candidates(candidates)

    assert len(merged) == 2
    assert merged[0]["equation_number"] == "5"
    assert merged[1]["equation_number"] is None
    assert "(6)" not in merged[0]["text"]


def test_load_paper_equation_manifest_returns_empty_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    payload = load_paper_equation_manifest(999)
    assert payload["num_equations"] == 0
    assert payload["equations"] == []
