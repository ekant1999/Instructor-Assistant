from pathlib import Path

from markdown_evaluation.scripts.normalize_outputs import normalize_markdown_document
from markdown_evaluation.scripts.score_outputs import score_normalized_doc
from markdown_evaluation.scripts._common import BenchmarkDoc


SAMPLE_MD = """# Sample Document

## Introduction

This introduction explains the problem and sets up the method.

### Method A

First method paragraph.

### Method B

### Method C

This paragraph belongs to Method C and should make Method B empty.

_Figure 1: Example caption._

## Results

The results show a clear gain.

_Table 2: Example table caption._
"""


def test_normalize_markdown_document_detects_empty_sections_and_duplicates():
    normalized = normalize_markdown_document(markdown=SAMPLE_MD, doc_id="pX", system="ia_phase1")
    metrics = normalized["intrinsic_metrics"]

    assert metrics["heading_count"] == 6
    assert metrics["empty_section_count"] == 2
    assert metrics["figure_caption_count"] == 1
    assert metrics["table_caption_count"] == 1
    assert metrics["consecutive_heading_run_count"] >= 1


def test_normalize_markdown_document_accepts_fig_abbreviation():
    normalized = normalize_markdown_document(
        markdown="## Intro\n\nFig. 1: Example caption.\n",
        doc_id="pFig",
        system="ia_phase1",
    )
    assert normalized["intrinsic_metrics"]["figure_caption_count"] == 1
    assert normalized["figures"][0]["number"] == 1


def test_normalize_markdown_document_strips_outline_prefixes_for_heading_match():
    normalized = normalize_markdown_document(
        markdown="# Doc\n\n### I. INTRODUCTION\n\nBody.\n\n### A. Overall Node Architecture\n\nMore body.\n",
        doc_id="pPrefix",
        system="ocr_agent",
    )

    assert [heading["normalized_text"] for heading in normalized["headings"]] == [
        "doc",
        "introduction",
        "overall node architecture",
    ]


def test_score_normalized_doc_scores_anchor_assignment():
    normalized = normalize_markdown_document(markdown=SAMPLE_MD, doc_id="pX", system="ia_phase1")
    gold = {
        "validated": True,
        "headings": [
            {"level": 2, "text": "Introduction"},
            {"level": 3, "text": "Method A"},
            {"level": 3, "text": "Method B"},
            {"level": 3, "text": "Method C"},
            {"level": 2, "text": "Results"},
        ],
        "section_anchors": [
            {"text": "This introduction explains the problem", "expected_section": "Introduction"},
            {"text": "The results show a clear gain", "expected_section": "Results"},
        ],
        "figures": [{"number": 1}],
        "tables": [{"number": 2}],
    }
    doc = BenchmarkDoc(doc_id="pX", pdf_path=Path("sample.pdf"), title="Sample")
    scored = score_normalized_doc(normalized, gold, doc)

    assert scored["gold_available"] is True
    assert scored["heading_f1"] > 0.9
    assert scored["anchor_recall"] == 1.0
    assert scored["anchor_assignment_accuracy"] == 1.0
    assert scored["figure_recall"] == 1.0
    assert scored["table_recall"] == 1.0
