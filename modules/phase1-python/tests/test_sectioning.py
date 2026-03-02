from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from ia_phase1 import sectioning


def test_canonicalize_heading_common_cases() -> None:
    assert sectioning.canonicalize_heading("1 Introduction") == "introduction"
    assert sectioning.canonicalize_heading("References") == "references"
    assert sectioning.canonicalize_heading("System Architecture") == "system_architecture"


def test_annotate_blocks_prefers_pdf_toc_when_coverage_is_strong(
    sample_pdf: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocks = [
        {"text": "Front matter", "page_no": 1, "block_index": 0, "bbox": None, "metadata": {}},
        {"text": "Intro starts", "page_no": 1, "block_index": 1, "bbox": None, "metadata": {}},
        {"text": "Method starts", "page_no": 2, "block_index": 0, "bbox": None, "metadata": {}},
        {"text": "Experiments starts", "page_no": 3, "block_index": 0, "bbox": None, "metadata": {}},
    ]

    toc_headings = [
        sectioning.HeadingCandidate("Introduction", 1, "pdf_toc", 0.97, page_hint=1),
        sectioning.HeadingCandidate("Method", 1, "pdf_toc", 0.97, page_hint=2),
        sectioning.HeadingCandidate("Experiments", 1, "pdf_toc", 0.97, page_hint=3),
    ]

    def fake_align(headings: List[sectioning.HeadingCandidate], _blocks):
        if headings and headings[0].source == "pdf_toc":
            return [
                sectioning.SectionSpan(0, "Introduction", "introduction", 1, "pdf_toc", 0.95, 1, 1, 1, 1),
                sectioning.SectionSpan(1, "Method", "methodology", 1, "pdf_toc", 0.95, 2, 2, 2, 2),
                sectioning.SectionSpan(2, "Experiments", "experiments", 1, "pdf_toc", 0.95, 3, 3, 3, 3),
            ]
        return []

    monkeypatch.setattr(sectioning, "_extract_headings_from_pdf_toc", lambda _pdf: toc_headings)
    monkeypatch.setattr(sectioning, "_extract_headings_from_arxiv_source", lambda _url, pdf_path=None: [])
    monkeypatch.setattr(sectioning, "_extract_headings_with_grobid", lambda _pdf: [])
    monkeypatch.setattr(sectioning, "_extract_heuristic_headings", lambda _blocks: [])
    monkeypatch.setattr(sectioning, "_align_headings_to_spans", fake_align)
    monkeypatch.setattr(sectioning, "_extract_document_title", lambda _pdf, _blocks: "")

    report = sectioning.annotate_blocks_with_sections(blocks, sample_pdf)
    assert report["strategy"] == "pdf_toc"
    assert len(report["sections"]) == 3
    assert blocks[1]["metadata"]["section_canonical"] == "introduction"
    assert blocks[2]["metadata"]["section_canonical"] == "methodology"


def test_annotate_blocks_uses_fallback_when_no_headings(
    sample_pdf: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocks = [
        {"text": "No heading text", "page_no": 1, "block_index": 0, "bbox": None, "metadata": {}},
        {"text": "More content", "page_no": 1, "block_index": 1, "bbox": None, "metadata": {}},
    ]

    monkeypatch.setattr(sectioning, "_extract_headings_from_pdf_toc", lambda _pdf: [])
    monkeypatch.setattr(sectioning, "_extract_headings_from_arxiv_source", lambda _url, pdf_path=None: [])
    monkeypatch.setattr(sectioning, "_extract_headings_with_grobid", lambda _pdf: [])
    monkeypatch.setattr(sectioning, "_extract_heuristic_headings", lambda _blocks: [])
    monkeypatch.setattr(sectioning, "_align_headings_to_spans", lambda _headings, _blocks: [])
    monkeypatch.setattr(sectioning, "_extract_document_title", lambda _pdf, _blocks: "")

    report = sectioning.annotate_blocks_with_sections(blocks, sample_pdf)
    assert report["strategy"] == "heuristic"
    assert len(report["sections"]) == 0
    assert blocks[0]["metadata"]["section_canonical"] == "other"
    assert blocks[0]["metadata"]["section_source"] == "fallback"


def test_extract_arxiv_id_from_pdf_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeReader:
        metadata = {
            "/arXivID": "https://arxiv.org/abs/2602.22094v1",
            "/Title": "Sample Title",
        }

    monkeypatch.setattr(sectioning, "PdfReader", lambda _path: FakeReader())
    assert sectioning._extract_arxiv_id_from_pdf_metadata(Path("/tmp/fake.pdf")) == "2602.22094v1"


def test_extract_heuristic_headings_detects_split_numbered_heading() -> None:
    blocks = [
        {
            "text": "3",
            "page_no": 1,
            "block_index": 0,
            "bbox": None,
            "metadata": {
                "first_line": "3",
                "line_count": 1,
                "char_count": 1,
                "max_font_size": 12.0,
                "avg_font_size": 12.0,
                "bold_ratio": 0.0,
            },
        },
        {
            "text": "Problem Definition",
            "page_no": 1,
            "block_index": 1,
            "bbox": None,
            "metadata": {
                "first_line": "Problem Definition",
                "line_count": 1,
                "char_count": 18,
                "max_font_size": 12.2,
                "avg_font_size": 12.2,
                "bold_ratio": 0.35,
            },
        },
        {
            "text": "This paragraph is long enough to act as body text for baseline font detection. " * 3,
            "page_no": 1,
            "block_index": 2,
            "bbox": None,
            "metadata": {
                "first_line": "This paragraph is long enough to act as body text for baseline font detection.",
                "line_count": 4,
                "char_count": 220,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
    ]
    headings = sectioning._extract_heuristic_headings(blocks)
    titles = [heading.title for heading in headings]
    assert "Problem Definition" in titles


def test_annotate_blocks_prefers_arxiv_source_over_shallow_pdf_toc(
    sample_pdf: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocks = [
        {"text": "Abstract block", "page_no": 1, "block_index": 0, "bbox": None, "metadata": {}},
        {"text": "Introduction block", "page_no": 2, "block_index": 0, "bbox": None, "metadata": {}},
        {"text": "Problem definition block", "page_no": 3, "block_index": 0, "bbox": None, "metadata": {}},
        {"text": "References block", "page_no": 4, "block_index": 0, "bbox": None, "metadata": {}},
    ]

    toc_headings = [
        sectioning.HeadingCandidate(
            "Petri Net Relaxation for Infeasibility Explanation and Sequential Task Planning",
            1,
            "pdf_toc",
            0.97,
            page_hint=1,
        ),
    ]
    heuristic_headings = [
        sectioning.HeadingCandidate("Abstract", 1, "heuristic", 0.72, page_hint=1),
        sectioning.HeadingCandidate("References", 1, "heuristic", 0.72, page_hint=4),
    ]
    arxiv_headings = [
        sectioning.HeadingCandidate("Abstract", 1, "arxiv_source", 0.95, page_hint=1),
        sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92, page_hint=2),
        sectioning.HeadingCandidate("Problem Definition", 1, "arxiv_source", 0.92, page_hint=3),
        sectioning.HeadingCandidate("References", 1, "arxiv_source", 0.9, page_hint=4),
    ]

    def fake_align(headings: List[sectioning.HeadingCandidate], _blocks):
        if not headings:
            return []
        if all(item.source == "arxiv_source" for item in headings):
            return [
                sectioning.SectionSpan(0, "Abstract", "abstract", 1, "arxiv_source", 0.94, 0, 0, 1, 1),
                sectioning.SectionSpan(1, "Introduction", "introduction", 1, "arxiv_source", 0.94, 1, 1, 2, 2),
                sectioning.SectionSpan(2, "Problem Definition", "problem_definition", 1, "arxiv_source", 0.94, 2, 2, 3, 3),
                sectioning.SectionSpan(3, "References", "references", 1, "arxiv_source", 0.93, 3, 3, 4, 4),
            ]
        if any(item.source == "pdf_toc" for item in headings):
            return [
                sectioning.SectionSpan(0, "front", "front_matter", 1, "fallback", 0.4, 0, 0, 1, 1),
                sectioning.SectionSpan(1, "Abstract", "abstract", 1, "heuristic", 0.8, 1, 2, 2, 3),
                sectioning.SectionSpan(
                    2,
                    "Petri Net Relaxation for Infeasibility Explanation and Sequential Task Planning",
                    "petri_net_relaxation_for_infeasibility_explanation_and_sequential_task_planning",
                    1,
                    "pdf_toc",
                    0.84,
                    2,
                    2,
                    3,
                    3,
                ),
                sectioning.SectionSpan(3, "References", "references", 1, "heuristic", 0.8, 3, 3, 4, 4),
            ]
        return []

    monkeypatch.setattr(sectioning, "_extract_headings_from_pdf_toc", lambda _pdf: toc_headings)
    monkeypatch.setattr(sectioning, "_extract_heuristic_headings", lambda _blocks: heuristic_headings)
    monkeypatch.setattr(sectioning, "_extract_headings_from_arxiv_source", lambda _url, pdf_path=None: arxiv_headings)
    monkeypatch.setattr(sectioning, "_extract_headings_with_grobid", lambda _pdf: [])
    monkeypatch.setattr(sectioning, "_extract_document_title", lambda _pdf, _blocks: "petri net relaxation for infeasibility explanation and sequential task planning")
    monkeypatch.setattr(sectioning, "_align_headings_to_spans", fake_align)

    report = sectioning.annotate_blocks_with_sections(blocks, sample_pdf, source_url="https://arxiv.org/abs/2602.22094v1")
    assert report["strategy"] == "arxiv_source"
    assert blocks[2]["metadata"]["section_canonical"] == "problem_definition"
