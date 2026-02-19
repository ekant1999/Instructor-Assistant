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
    monkeypatch.setattr(sectioning, "_extract_headings_from_arxiv_source", lambda _url: [])
    monkeypatch.setattr(sectioning, "_extract_headings_with_grobid", lambda _pdf: [])
    monkeypatch.setattr(sectioning, "_extract_heuristic_headings", lambda _blocks: [])
    monkeypatch.setattr(sectioning, "_align_headings_to_spans", fake_align)

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
    monkeypatch.setattr(sectioning, "_extract_headings_from_arxiv_source", lambda _url: [])
    monkeypatch.setattr(sectioning, "_extract_headings_with_grobid", lambda _pdf: [])
    monkeypatch.setattr(sectioning, "_extract_heuristic_headings", lambda _blocks: [])
    monkeypatch.setattr(sectioning, "_align_headings_to_spans", lambda _headings, _blocks: [])

    report = sectioning.annotate_blocks_with_sections(blocks, sample_pdf)
    assert report["strategy"] == "heuristic"
    assert len(report["sections"]) == 0
    assert blocks[0]["metadata"]["section_canonical"] == "other"
    assert blocks[0]["metadata"]["section_source"] == "fallback"
