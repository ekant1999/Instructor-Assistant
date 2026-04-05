from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from improved_ocr_agent.non_ocr_routing import PageContentProfile, _smooth_isolated_page_runs, build_document_content_profile


def _make_page(
    page_num: int,
    *,
    heading_lines=None,
    top_lines=None,
    bottom_lines=None,
    citation_count: int = 0,
    figure_caption_count: int = 0,
    table_caption_count: int = 0,
    equation_line_count: int = 0,
    author_affiliation_hits: int = 0,
    image_count: int = 0,
    table_count: int = 0,
    drawing_count: int = 0,
    text_len: int = 600,
    two_columns: bool = False,
    paragraph_like_count: int = 0,
):
    return {
        "page_num": page_num,
        "heading_lines": heading_lines or [],
        "top_lines": top_lines or [],
        "bottom_lines": bottom_lines or [],
        "citation_count": citation_count,
        "figure_caption_count": figure_caption_count,
        "table_caption_count": table_caption_count,
        "equation_line_count": equation_line_count,
        "author_affiliation_hits": author_affiliation_hits,
        "image_count": image_count,
        "table_count": table_count,
        "drawing_count": drawing_count,
        "text_len": text_len,
        "two_columns": two_columns,
        "paragraph_like_count": paragraph_like_count,
    }


def test_non_ocr_routing_prefers_ia_phase1_for_scholarly_document() -> None:
    pages = [
        _make_page(
            1,
            heading_lines=["Abstract", "Introduction"],
            citation_count=3,
            author_affiliation_hits=2,
            figure_caption_count=1,
            text_len=1200,
            two_columns=True,
        ),
        _make_page(
            2,
            heading_lines=["Method", "Results"],
            citation_count=2,
            equation_line_count=3,
            table_caption_count=1,
            text_len=1300,
            two_columns=True,
        ),
        _make_page(
            3,
            heading_lines=["Conclusion", "References"],
            citation_count=2,
            text_len=900,
            two_columns=True,
        ),
    ]

    profile = build_document_content_profile(pages, total_pages=3)

    assert profile.document_handler == "ia_phase1"
    assert all(page.handler == "ia_phase1" for page in profile.page_profiles)


def test_non_ocr_routing_prefers_native_for_textheavy_report() -> None:
    footer = ["Case Review Report - Page 1"]
    pages = [
        _make_page(
            1,
            heading_lines=["Section 1: Background"],
            top_lines=["Case Review Report"],
            bottom_lines=footer,
            paragraph_like_count=6,
            text_len=1400,
        ),
        _make_page(
            2,
            heading_lines=["Section 2: Findings"],
            top_lines=["Case Review Report"],
            bottom_lines=["Case Review Report - Page 2"],
            paragraph_like_count=6,
            text_len=1300,
        ),
        _make_page(
            3,
            heading_lines=["Section 3: Recommendations"],
            top_lines=["Case Review Report"],
            bottom_lines=["Case Review Report - Page 3"],
            paragraph_like_count=5,
            text_len=1250,
        ),
    ]

    profile = build_document_content_profile(pages, total_pages=3)

    assert profile.document_handler == "native"
    assert all(page.handler == "native" for page in profile.page_profiles)


def test_non_ocr_routing_prefers_ia_phase1_for_structured_visual_report() -> None:
    pages = [
        _make_page(
            1,
            heading_lines=["Section 1: System Overview"],
            figure_caption_count=2,
            image_count=2,
            drawing_count=10,
            text_len=800,
        ),
        _make_page(
            2,
            heading_lines=["Section 2: Results"],
            table_caption_count=1,
            table_count=1,
            image_count=1,
            text_len=700,
        ),
    ]

    profile = build_document_content_profile(pages, total_pages=2)

    assert profile.document_handler == "ia_phase1"
    assert all(page.handler == "ia_phase1" for page in profile.page_profiles)


def test_non_ocr_routing_prefers_ia_phase1_for_one_column_research_without_citations() -> None:
    pages = [
        _make_page(
            1,
            heading_lines=[
                "A Strong One-Column Research Paper",
                "1. Introduction",
            ],
            top_lines=[
                "A Strong One-Column Research Paper",
                "Research Lab, Example University",
            ],
            author_affiliation_hits=2,
            paragraph_like_count=8,
            text_len=2600,
        ),
        _make_page(
            2,
            heading_lines=[
                "2. Preliminaries",
                "2.1. Problem Formulation",
                "2.2. Optimization Objective",
            ],
            equation_line_count=8,
            paragraph_like_count=8,
            text_len=2500,
        ),
        _make_page(
            3,
            heading_lines=[
                "3. Experiments",
                "3.1. Main Results",
            ],
            figure_caption_count=1,
            table_caption_count=1,
            image_count=1,
            paragraph_like_count=7,
            text_len=2200,
        ),
    ]

    profile = build_document_content_profile(pages, total_pages=3)

    assert profile.document_handler == "ia_phase1"
    assert all(page.handler == "ia_phase1" for page in profile.page_profiles)


def test_non_ocr_routing_smooths_isolated_page_runs() -> None:
    pages = [
        PageContentProfile(page_num=1, ia_score=0, native_score=5, handler="native"),
        PageContentProfile(page_num=2, ia_score=4, native_score=1, handler="ia_phase1"),
        PageContentProfile(page_num=3, ia_score=0, native_score=5, handler="native"),
    ]

    smoothed = _smooth_isolated_page_runs(pages, total_pages=3)

    assert [page.handler for page in smoothed] == ["native", "native", "native"]
