from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from ia_phase1 import sectioning


def test_canonicalize_heading_common_cases() -> None:
    assert sectioning.canonicalize_heading("1 Introduction") == "introduction"
    assert sectioning.canonicalize_heading("Related Works") == "related_work"
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


def test_extract_heuristic_headings_filters_dense_figure_labels() -> None:
    blocks = [
        {
            "text": "Source Video",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 170, "y0": 170, "x1": 310, "y1": 198},
            "metadata": {
                "first_line": "Source Video",
                "line_count": 1,
                "char_count": 12,
                "max_font_size": 12.6,
                "avg_font_size": 12.4,
                "bold_ratio": 0.52,
            },
        },
        {
            "text": "Input Noise",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 375, "y0": 172, "x1": 505, "y1": 200},
            "metadata": {
                "first_line": "Input Noise",
                "line_count": 1,
                "char_count": 11,
                "max_font_size": 12.4,
                "avg_font_size": 12.3,
                "bold_ratio": 0.5,
            },
        },
        {
            "text": "Text Prompt",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 274, "y0": 240, "x1": 398, "y1": 268},
            "metadata": {
                "first_line": "Text Prompt",
                "line_count": 1,
                "char_count": 11,
                "max_font_size": 12.5,
                "avg_font_size": 12.4,
                "bold_ratio": 0.47,
            },
        },
        {
            "text": "Edited Video",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 520, "y0": 260, "x1": 658, "y1": 288},
            "metadata": {
                "first_line": "Edited Video",
                "line_count": 1,
                "char_count": 12,
                "max_font_size": 12.3,
                "avg_font_size": 12.2,
                "bold_ratio": 0.49,
            },
        },
        {
            "text": "Background Video",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 65, "y0": 257, "x1": 230, "y1": 286},
            "metadata": {
                "first_line": "Background Video",
                "line_count": 1,
                "char_count": 16,
                "max_font_size": 12.4,
                "avg_font_size": 12.3,
                "bold_ratio": 0.51,
            },
        },
        {
            "text": "3 Method",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 62, "y0": 86, "x1": 210, "y1": 112},
            "metadata": {
                "first_line": "3 Method",
                "line_count": 1,
                "char_count": 8,
                "max_font_size": 12.8,
                "avg_font_size": 12.7,
                "bold_ratio": 0.45,
            },
        },
        {
            "text": "This section explains the method in detail and contains enough prose to count as body text. " * 2,
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 62, "y0": 126, "x1": 550, "y1": 216},
            "metadata": {
                "first_line": "This section explains the method in detail and contains enough prose to count as body text.",
                "line_count": 4,
                "char_count": 210,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
    ]
    headings = sectioning._extract_heuristic_headings(blocks)
    titles = [h.title for h in headings]
    assert "Method" in titles
    assert "Source Video" not in titles
    assert "Input Noise" not in titles
    assert "Edited Video" not in titles


def test_extract_heuristic_headings_keeps_unnumbered_heading_with_body_followup() -> None:
    blocks = [
        {
            "text": "Related Work",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 62, "y0": 90, "x1": 205, "y1": 116},
            "metadata": {
                "first_line": "Related Work",
                "line_count": 1,
                "char_count": 12,
                "max_font_size": 12.3,
                "avg_font_size": 12.2,
                "bold_ratio": 0.46,
            },
        },
        {
            "text": "Prior approaches focus on task planning constraints and symbolic reasoning over action models. " * 2,
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 62, "y0": 130, "x1": 540, "y1": 214},
            "metadata": {
                "first_line": "Prior approaches focus on task planning constraints and symbolic reasoning over action models.",
                "line_count": 3,
                "char_count": 180,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
    ]
    headings = sectioning._extract_heuristic_headings(blocks)
    titles = [h.title for h in headings]
    assert "Related Work" in titles


def test_seed_heading_page_hints_from_heuristic_reference() -> None:
    target = [
        sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92),
        sectioning.HeadingCandidate("Problem Definition", 1, "arxiv_source", 0.92),
        sectioning.HeadingCandidate("References", 1, "arxiv_source", 0.9),
    ]
    reference = [
        sectioning.HeadingCandidate("1 Introduction", 1, "heuristic", 0.72, page_hint=2),
        sectioning.HeadingCandidate("3 Problem Definition", 1, "heuristic", 0.72, page_hint=5),
        sectioning.HeadingCandidate("References", 1, "heuristic", 0.72, page_hint=21),
    ]

    seeded = sectioning._seed_heading_page_hints(target, reference)
    assert [item.page_hint for item in seeded] == [2, 5, 21]


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


def test_align_headings_prefers_heading_anchor_over_page_start_body_match() -> None:
    blocks = [
        {
            "text": "3 Problem Definition",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 80, "x1": 260, "y1": 102},
            "metadata": {
                "first_line": "3 Problem Definition",
                "line_count": 1,
                "char_count": 20,
                "max_font_size": 12.4,
                "avg_font_size": 12.4,
                "bold_ratio": 0.42,
            },
        },
        {
            "text": "We define one-shot and then sequential planning as a process.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 60, "y0": 120, "x1": 520, "y1": 180},
            "metadata": {
                "first_line": "We define one-shot and then sequential planning as a process.",
                "line_count": 3,
                "char_count": 160,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
        {
            "text": "In the background we discuss prior work and background assumptions first.",
            "page_no": 3,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 70, "x1": 520, "y1": 122},
            "metadata": {
                "first_line": "In the background we discuss prior work and background assumptions first.",
                "line_count": 3,
                "char_count": 170,
                "max_font_size": 10.1,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
        {
            "text": "4 Background",
            "page_no": 3,
            "block_index": 1,
            "bbox": {"x0": 60, "y0": 150, "x1": 230, "y1": 172},
            "metadata": {
                "first_line": "4 Background",
                "line_count": 1,
                "char_count": 12,
                "max_font_size": 12.3,
                "avg_font_size": 12.2,
                "bold_ratio": 0.4,
            },
        },
        {
            "text": "Background section details and symbols.",
            "page_no": 3,
            "block_index": 2,
            "bbox": {"x0": 60, "y0": 188, "x1": 500, "y1": 240},
            "metadata": {
                "first_line": "Background section details and symbols.",
                "line_count": 2,
                "char_count": 98,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
    ]

    headings = [
        sectioning.HeadingCandidate("Problem Definition", 1, "pdf_toc", 0.97, page_hint=2),
        sectioning.HeadingCandidate("Background", 1, "pdf_toc", 0.97, page_hint=3),
    ]

    spans = sectioning._align_headings_to_spans(headings, blocks)
    assert len(spans) >= 2
    problem_span = next(span for span in spans if span.canonical == "problem_definition")
    background_span = next(span for span in spans if span.canonical == "background")

    assert problem_span.start_idx == 0
    # Crucial check: anchor should be the heading block, not page-start prose block.
    assert background_span.start_idx == 3


def test_align_headings_without_page_hint_prefers_exact_heading_line() -> None:
    blocks = [
        {
            "text": "We solve planning and introduce a problem definition in this paragraph.",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 90, "x1": 520, "y1": 150},
            "metadata": {
                "first_line": "We solve planning and introduce a problem definition in this paragraph.",
                "line_count": 3,
                "char_count": 162,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
        {
            "text": "3 Problem Definition",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 60, "y0": 180, "x1": 260, "y1": 202},
            "metadata": {
                "first_line": "3 Problem Definition",
                "line_count": 1,
                "char_count": 20,
                "max_font_size": 12.4,
                "avg_font_size": 12.4,
                "bold_ratio": 0.42,
            },
        },
    ]
    headings = [sectioning.HeadingCandidate("Problem Definition", 1, "arxiv_source", 0.92)]
    spans = sectioning._align_headings_to_spans(headings, blocks)
    assert spans
    target = next(span for span in spans if span.canonical == "problem_definition")
    assert target.start_idx == 1


def test_align_headings_without_page_hint_avoids_midline_phrase_mentions() -> None:
    blocks = [
        {
            "text": "Abstract. Plans often change due to changes in the situation.",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 80, "x1": 520, "y1": 126},
            "metadata": {
                "first_line": "Abstract. Plans often change due to changes in the situation.",
                "line_count": 2,
                "char_count": 120,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
        {
            "text": "1 Introduction",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 60, "y0": 140, "x1": 250, "y1": 164},
            "metadata": {
                "first_line": "1 Introduction",
                "line_count": 1,
                "char_count": 14,
                "max_font_size": 12.2,
                "avg_font_size": 12.2,
                "bold_ratio": 0.44,
            },
        },
        {
            "text": "We describe prior approaches and define our assumptions.",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 60, "y0": 178, "x1": 520, "y1": 236},
            "metadata": {
                "first_line": "We describe prior approaches and define our assumptions.",
                "line_count": 3,
                "char_count": 155,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
        {
            "text": "24. De Moura, L., Bjørner, N.: Satisfiability modulo theories: introduction and applications.",
            "page_no": 4,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 90, "x1": 520, "y1": 132},
            "metadata": {
                "first_line": "24. De Moura, L., Bjørner, N.: Satisfiability modulo theories: introduction and applications.",
                "line_count": 2,
                "char_count": 170,
                "max_font_size": 10.0,
                "avg_font_size": 10.0,
                "bold_ratio": 0.0,
            },
        },
    ]
    headings = [sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92)]
    spans = sectioning._align_headings_to_spans(headings, blocks)
    assert spans
    intro_span = next(span for span in spans if span.canonical == "introduction")
    assert intro_span.start_idx == 1


def test_strategy_score_prefers_structured_source_over_noisy_heuristic() -> None:
    arxiv_headings = [
        sectioning.HeadingCandidate("Abstract", 1, "arxiv_source", 0.95, page_hint=1),
        sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92, page_hint=2),
        sectioning.HeadingCandidate("Related Work", 1, "arxiv_source", 0.92, page_hint=3),
        sectioning.HeadingCandidate("Methodology", 1, "arxiv_source", 0.92, page_hint=4),
        sectioning.HeadingCandidate("Experiments", 1, "arxiv_source", 0.92, page_hint=5),
        sectioning.HeadingCandidate("Conclusion", 1, "arxiv_source", 0.92, page_hint=6),
        sectioning.HeadingCandidate("References", 1, "arxiv_source", 0.9, page_hint=7),
    ]
    arxiv_spans = [
        sectioning.SectionSpan(0, "Abstract", "abstract", 1, "arxiv_source", 0.93, 0, 2, 1, 1),
        sectioning.SectionSpan(1, "Introduction", "introduction", 1, "arxiv_source", 0.92, 3, 7, 2, 2),
        sectioning.SectionSpan(2, "Related Work", "related_work", 1, "arxiv_source", 0.92, 8, 10, 3, 3),
        sectioning.SectionSpan(3, "Methodology", "methodology", 1, "arxiv_source", 0.92, 11, 18, 4, 4),
        sectioning.SectionSpan(4, "Experiments", "experiments", 1, "arxiv_source", 0.92, 19, 28, 5, 5),
        sectioning.SectionSpan(5, "Conclusion", "conclusion", 1, "arxiv_source", 0.92, 29, 34, 6, 6),
        sectioning.SectionSpan(6, "References", "references", 1, "arxiv_source", 0.9, 35, 45, 7, 8),
    ]

    heuristic_headings = [
        sectioning.HeadingCandidate("Abstract", 1, "heuristic", 0.72, page_hint=1),
        sectioning.HeadingCandidate("Source Video", 1, "heuristic", 0.72, page_hint=4),
        sectioning.HeadingCandidate("Input Noise", 1, "heuristic", 0.72, page_hint=4),
        sectioning.HeadingCandidate("Text Prompt", 1, "heuristic", 0.72, page_hint=4),
        sectioning.HeadingCandidate("Edited Video", 1, "heuristic", 0.72, page_hint=4),
        sectioning.HeadingCandidate("Related Works", 1, "heuristic", 0.72, page_hint=3),
        sectioning.HeadingCandidate("Methodology", 1, "heuristic", 0.72, page_hint=4),
        sectioning.HeadingCandidate("Experiments", 1, "heuristic", 0.72, page_hint=5),
        sectioning.HeadingCandidate("Conclusion", 1, "heuristic", 0.72, page_hint=6),
        sectioning.HeadingCandidate("References", 1, "heuristic", 0.72, page_hint=7),
    ]
    heuristic_spans = [
        sectioning.SectionSpan(0, "Abstract", "abstract", 1, "heuristic", 0.89, 0, 2, 1, 1),
        sectioning.SectionSpan(1, "Related Works", "related_work", 1, "heuristic", 0.89, 3, 7, 3, 3),
        sectioning.SectionSpan(2, "Source Video", "source_video", 1, "heuristic", 0.89, 8, 9, 4, 4),
        sectioning.SectionSpan(3, "Input Noise", "input_noise", 1, "heuristic", 0.89, 10, 11, 4, 4),
        sectioning.SectionSpan(4, "Text Prompt", "text_prompt", 1, "heuristic", 0.89, 12, 13, 4, 4),
        sectioning.SectionSpan(5, "Edited Video", "edited_video", 1, "heuristic", 0.89, 14, 16, 4, 4),
        sectioning.SectionSpan(6, "Methodology", "methodology", 1, "heuristic", 0.89, 17, 22, 4, 4),
        sectioning.SectionSpan(7, "Experiments", "experiments", 1, "heuristic", 0.89, 23, 30, 5, 5),
        sectioning.SectionSpan(8, "Conclusion", "conclusion", 1, "heuristic", 0.89, 31, 35, 6, 6),
        sectioning.SectionSpan(9, "References", "references", 1, "heuristic", 0.89, 36, 45, 7, 8),
    ]

    arxiv_score = sectioning._strategy_score(
        "arxiv_source",
        arxiv_headings,
        arxiv_spans,
        total_pages=8,
        document_title_norm="editctrl disentangled local and global control for real time generative video editing",
    )
    heuristic_score = sectioning._strategy_score(
        "heuristic",
        heuristic_headings,
        heuristic_spans,
        total_pages=8,
        document_title_norm="editctrl disentangled local and global control for real time generative video editing",
    )

    assert arxiv_score > heuristic_score


def test_fill_missing_heading_page_hints_uses_neighbor_order() -> None:
    headings = [
        sectioning.HeadingCandidate("Abstract", 1, "arxiv_source", 0.95, page_hint=1),
        sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92, page_hint=None),
        sectioning.HeadingCandidate("Related Work", 1, "arxiv_source", 0.92, page_hint=2),
        sectioning.HeadingCandidate("Method", 1, "arxiv_source", 0.92, page_hint=5),
        sectioning.HeadingCandidate("Conclusion", 1, "arxiv_source", 0.92, page_hint=None),
    ]

    filled = sectioning._fill_missing_heading_page_hints(headings, total_pages=21)
    assert [item.page_hint for item in filled] == [1, 2, 2, 5, 5]


def test_align_headings_unhinted_title_is_bounded_by_next_hinted_page() -> None:
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 80, "x1": 210, "y1": 102},
            "metadata": {"first_line": "Abstract", "line_count": 1, "char_count": 8, "max_font_size": 12.3, "avg_font_size": 12.3, "bold_ratio": 0.4},
        },
        {
            "text": "2 Related Work",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 92, "x1": 230, "y1": 114},
            "metadata": {"first_line": "2 Related Work", "line_count": 1, "char_count": 14, "max_font_size": 12.2, "avg_font_size": 12.2, "bold_ratio": 0.4},
        },
        {
            "text": "3 Problem Definition",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 60, "y0": 132, "x1": 280, "y1": 156},
            "metadata": {"first_line": "3 Problem Definition", "line_count": 1, "char_count": 20, "max_font_size": 12.2, "avg_font_size": 12.2, "bold_ratio": 0.41},
        },
        {
            "text": "24. Satisfiability modulo theories: introduction and applications.",
            "page_no": 18,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 92, "x1": 520, "y1": 126},
            "metadata": {"first_line": "24. Satisfiability modulo theories: introduction and applications.", "line_count": 2, "char_count": 120, "max_font_size": 10.0, "avg_font_size": 10.0, "bold_ratio": 0.0},
        },
        {
            "text": "Conclusion",
            "page_no": 19,
            "block_index": 0,
            "bbox": {"x0": 60, "y0": 88, "x1": 230, "y1": 110},
            "metadata": {"first_line": "Conclusion", "line_count": 1, "char_count": 10, "max_font_size": 12.1, "avg_font_size": 12.1, "bold_ratio": 0.4},
        },
    ]
    headings = [
        sectioning.HeadingCandidate("Abstract", 1, "arxiv_source", 0.95, page_hint=1),
        sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92, page_hint=None),
        sectioning.HeadingCandidate("Related Work", 1, "arxiv_source", 0.92, page_hint=2),
        sectioning.HeadingCandidate("Problem Definition", 1, "arxiv_source", 0.92, page_hint=2),
        sectioning.HeadingCandidate("Conclusion", 1, "arxiv_source", 0.92, page_hint=19),
    ]
    headings = sectioning._fill_missing_heading_page_hints(headings, total_pages=21)
    spans = sectioning._align_headings_to_spans(headings, blocks)
    intro_span = next(span for span in spans if span.canonical == "introduction")
    assert intro_span.start_page <= 3


def test_strategy_score_penalizes_pathological_abstract_overreach() -> None:
    headings = [
        sectioning.HeadingCandidate("Abstract", 1, "arxiv_source", 0.95, page_hint=1),
        sectioning.HeadingCandidate("Introduction", 1, "arxiv_source", 0.92, page_hint=2),
        sectioning.HeadingCandidate("Related Work", 1, "arxiv_source", 0.92, page_hint=3),
        sectioning.HeadingCandidate("Problem Definition", 1, "arxiv_source", 0.92, page_hint=4),
        sectioning.HeadingCandidate("Method", 1, "arxiv_source", 0.92, page_hint=6),
        sectioning.HeadingCandidate("Experiments", 1, "arxiv_source", 0.92, page_hint=12),
        sectioning.HeadingCandidate("Conclusion", 1, "arxiv_source", 0.92, page_hint=17),
        sectioning.HeadingCandidate("References", 1, "arxiv_source", 0.9, page_hint=18),
    ]
    healthy_spans = [
        sectioning.SectionSpan(0, "Abstract", "abstract", 1, "arxiv_source", 0.93, 0, 6, 1, 1),
        sectioning.SectionSpan(1, "Introduction", "introduction", 1, "arxiv_source", 0.92, 7, 24, 2, 3),
        sectioning.SectionSpan(2, "Problem Definition", "problem_definition", 1, "arxiv_source", 0.92, 25, 52, 4, 5),
        sectioning.SectionSpan(3, "Method", "methodology", 1, "arxiv_source", 0.92, 53, 130, 6, 12),
        sectioning.SectionSpan(4, "Experiments", "experiments", 1, "arxiv_source", 0.92, 131, 170, 12, 16),
        sectioning.SectionSpan(5, "Conclusion", "conclusion", 1, "arxiv_source", 0.92, 171, 185, 17, 17),
        sectioning.SectionSpan(6, "References", "references", 1, "arxiv_source", 0.9, 186, 220, 18, 21),
    ]
    pathological_spans = [
        sectioning.SectionSpan(0, "Abstract", "abstract", 1, "arxiv_source", 0.93, 0, 185, 1, 18),
        sectioning.SectionSpan(1, "Introduction", "introduction", 1, "arxiv_source", 0.9, 186, 190, 18, 18),
        sectioning.SectionSpan(2, "Conclusion", "conclusion", 1, "arxiv_source", 0.9, 191, 220, 19, 21),
    ]

    healthy_score = sectioning._strategy_score(
        "arxiv_source",
        headings,
        healthy_spans,
        total_pages=21,
        document_title_norm="petri net relaxation for infeasibility explanation and sequential task planning",
    )
    pathological_score = sectioning._strategy_score(
        "arxiv_source",
        headings,
        pathological_spans,
        total_pages=21,
        document_title_norm="petri net relaxation for infeasibility explanation and sequential task planning",
    )
    assert healthy_score > pathological_score
