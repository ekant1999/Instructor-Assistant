from improved_ocr_agent.quality import audit_document_model
from improved_ocr_agent.sectioning import build_document_model, normalize_markdown


def test_quality_audit_flags_duplicate_and_empty_headings() -> None:
    model = build_document_model(
        "\n".join(
            [
                "## Results",
                "## RQ1: Overall Performance",
                "## RQ2: Efficiency",
                "## Results",
                "Final results text.",
            ]
        ),
        title_hint="WRITEBACK-RAG",
    )

    audit = audit_document_model(model)

    assert audit.empty_section_count >= 2
    assert audit.consecutive_empty_heading_runs >= 2
    assert "Results" in audit.duplicate_headings
    assert audit.needs_conservative_fallback


def test_conservative_fallback_absorbs_low_confidence_empty_headings() -> None:
    markdown = normalize_markdown(
        "\n".join(
            [
                "## Introduction",
                "Intro text.",
                "## Table 2",
                "## RQ1: Overall Performance",
                "## RQ2: Efficiency",
                "Body text.",
            ]
        ),
        title_hint="WRITEBACK-RAG",
    )

    assert "## Table 2" not in markdown
    assert "## Introduction" in markdown
    assert "Body text." in markdown
