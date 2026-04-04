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


def test_normalize_markdown_document_extracts_ocr_figure_numbers_from_image_alt_text():
    normalized = normalize_markdown_document(
        markdown=(
            "# Doc\n\n"
            "## Results\n\n"
            "![Figure 3 on Page 2](doc_assets/figures/doc_page_2_fig_1.png)\n"
        ),
        doc_id="pAltFig",
        system="ocr_agent",
    )

    assert normalized["intrinsic_metrics"]["figure_caption_count"] == 1
    assert normalized["figures"][0]["number"] == 3


def test_normalize_markdown_document_extracts_roman_table_captions_and_table_alt_text():
    normalized = normalize_markdown_document(
        markdown=(
            "# Doc\n\n"
            "## Results\n\n"
            "**TABLE II PERFORMANCE OBTAINED WITH DIFFERENT GRAPHIC CARDS**\n\n"
            "![Table 2](doc_assets/tables/doc_page_4_table_caption_1.png)\n"
        ),
        doc_id="pRomanTable",
        system="improved_ocr_agent",
    )

    assert normalized["intrinsic_metrics"]["table_caption_count"] >= 1
    assert any(table["number"] == 2 for table in normalized["tables"])


def test_normalize_markdown_document_strips_outline_prefixes_for_heading_match():
    normalized = normalize_markdown_document(
        markdown=(
            "# Doc\n\n"
            "### I. INTRODUCTION\n\n"
            "Body.\n\n"
            "### A. Overall Node Architecture\n\n"
            "More body.\n\n"
            "### 4.1 Single-Frame 3D Reconstruction with Learned Priors\n\n"
            "Section body.\n\n"
            "### 2 Related Works\n\n"
            "Section body.\n\n"
            "### W RITE B ACK-RAG Prevents Answer Leakage\n\n"
            "Appendix body.\n"
        ),
        doc_id="pPrefix",
        system="ocr_agent",
    )

    assert [heading["normalized_text"] for heading in normalized["headings"]] == [
        "doc",
        "introduction",
        "overall node architecture",
        "single frame 3d reconstruction with learned priors",
        "related works",
        "write back rag prevents answer leakage",
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


def test_score_normalized_doc_matches_appendix_headings_with_letter_prefixes():
    normalized = normalize_markdown_document(
        markdown=(
            "# Doc\n\n"
            "### A On the Use of KB Training\n\n"
            "This appendix explains why write-back docs compete with the full corpus.\n"
        ),
        doc_id="pAppendix",
        system="ocr_agent",
    )
    gold = {
        "validated": True,
        "headings": [{"level": 2, "text": "On the Use of KB Training"}],
        "section_anchors": [
            {
                "text": "write-back docs compete with the full corpus",
                "expected_section": "On the Use of KB Training",
            }
        ],
        "figures": [],
        "tables": [],
    }
    doc = BenchmarkDoc(doc_id="pAppendix", pdf_path=Path("sample.pdf"), title="Sample")
    scored = score_normalized_doc(normalized, gold, doc)

    assert scored["heading_f1"] > 0.5
    assert scored["anchor_assignment_accuracy"] == 1.0


def test_score_normalized_doc_marks_asset_recall_na_when_gold_has_no_assets():
    normalized = normalize_markdown_document(markdown="# Doc\n\n## Intro\n\nSome prose.\n", doc_id="pNoAssets", system="ia_phase1")
    gold = {
        "validated": True,
        "headings": [{"level": 2, "text": "Intro"}],
        "section_anchors": [{"text": "Some prose", "expected_section": "Intro"}],
        "figures": [],
        "tables": [],
    }
    doc = BenchmarkDoc(doc_id="pNoAssets", pdf_path=Path("sample.pdf"), title="Sample")
    scored = score_normalized_doc(normalized, gold, doc)

    assert scored["figure_recall"] is None
    assert scored["table_recall"] is None
