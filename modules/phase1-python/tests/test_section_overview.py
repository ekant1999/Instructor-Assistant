from pathlib import Path

from ia_phase1.section_overview import (
    SectionOverviewConfig,
    build_section_overview,
    render_section_overview_markdown,
)


def _block(text: str, *, page_no: int, section_title: str, section_canonical: str, section_level: int = 1):
    return {
        "text": text,
        "page_no": page_no,
        "block_index": 0,
        "bbox": {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 20.0},
        "metadata": {
            "section_title": section_title,
            "section_canonical": section_canonical,
            "section_level": section_level,
        },
    }


def test_build_section_overview_skips_references_by_default(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "We introduce a practical method for section-level summarization. The approach produces compact summaries from clean prose blocks.",
            page_no=1,
            section_title="Introduction",
            section_canonical="introduction",
        ),
        _block(
            "[1] Smith et al. 2024. A paper title.",
            page_no=2,
            section_title="References",
            section_canonical="references",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    assert [item.section_title for item in result.sections] == ["Introduction"]
    assert result.sections[0].summary_paragraph.startswith("We introduce a practical method")


def test_build_section_overview_reflows_and_dehyphenates(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "Relying on in-domain annotations and precise sensor-rig pri-\nors, our method improves robustness across multiple benchmarks.\nIt also reduces manual tuning.",
            page_no=1,
            section_title="Abstract",
            section_canonical="abstract",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    assert result.sections
    summary = result.sections[0].summary_paragraph
    assert "priors" in summary
    assert "pri-\nors" not in summary


def test_build_section_overview_ignores_caption_noise_and_renders_markdown(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "Figure 2: Example qualitative comparison.",
            page_no=3,
            section_title="Experiments",
            section_canonical="experiments",
        ),
        _block(
            "We evaluate on three benchmarks and show that the proposed system improves accuracy while keeping latency low. The strongest gains appear on out-of-domain scenes.",
            page_no=3,
            section_title="Experiments",
            section_canonical="experiments",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    assert len(result.sections) == 1
    assert "Figure 2" not in result.sections[0].summary_paragraph

    markdown = render_section_overview_markdown(result)
    assert "## Experiments" in markdown
    assert "improves accuracy" in markdown


def test_build_section_overview_skips_code_like_lines(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "x_eye = torch.eye(lora_A.weight.shape [1], ...) # [d_in , d_in]",
            page_no=2,
            section_title="Introduction",
            section_canonical="introduction",
        ),
        _block(
            "We analyze the main bottleneck and show that the proposed implementation reduces memory traffic while preserving numerical stability.",
            page_no=2,
            section_title="Introduction",
            section_canonical="introduction",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    assert len(result.sections) == 1
    summary = result.sections[0].summary_paragraph
    assert "torch.eye" not in summary
    assert "reduces memory traffic" in summary


def test_build_section_overview_defaults_to_longer_section_paragraphs(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            (
                "We introduce a retrieval pipeline that aligns section boundaries with cleaned prose blocks. "
                "The system ranks candidate sentences using section-level term coverage and position-aware scoring. "
                "It then assembles a moderately detailed paragraph so each section overview captures the main idea, mechanism, and outcome."
            ),
            page_no=1,
            section_title="Method",
            section_canonical="methodology",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    assert len(result.sections) == 1
    summary = result.sections[0].summary_paragraph
    assert "aligns section boundaries" in summary
    assert "position-aware scoring" in summary
    assert len(summary.split()) >= 18


def test_build_section_overview_keeps_et_al_sentence_intact(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "Weight-Decomposed Low-Rank Adaptation (DoRA; Liu et al. [2024]) extends LoRA by decoupling weight magnitude from direction. We present a fused implementation that reduces memory traffic.",
            page_no=1,
            section_title="Abstract",
            section_canonical="abstract",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    summary = result.sections[0].summary_paragraph
    assert "Liu et al. [2024]) extends LoRA" in summary
    assert "Weight-Decomposed Low-Rank Adaptation" in summary


def test_build_section_overview_skips_reference_blocks_from_missectioned_content(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "We conclude that the proposed occupancy model improves zero-shot generalization across datasets.",
            page_no=8,
            section_title="Conclusion",
            section_canonical="conclusion",
        ),
        _block(
            "[14] Wanshui Gan et al. A comprehensive framework for 3d occupancy estimation in autonomous driving. IEEE TIV, 2024.",
            page_no=9,
            section_title="Conclusion",
            section_canonical="conclusion",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    summary = result.sections[0].summary_paragraph
    assert "zero-shot generalization" in summary
    assert "A comprehensive framework for 3d occupancy estimation" not in summary


def test_build_section_overview_strips_repeated_document_title_prefix(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "End-to-End Training for Unified Tokenization and Latent Denoising We propose an alternative perspective on joint training.",
            page_no=2,
            section_title="Introduction",
            section_canonical="introduction",
        ),
    ]

    result = build_section_overview(
        pdf_path,
        blocks=blocks,
        metadata={"title": "End-to-End Training for Unified Tokenization and Latent Denoising"},
        config=SectionOverviewConfig(),
    )

    summary = result.sections[0].summary_paragraph
    assert summary.startswith("We propose an alternative perspective")


def test_build_section_overview_uses_caption_fallback_for_qualitative_sections(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "C. Qualitative Examples",
            page_no=16,
            section_title="Qualitative Examples",
            section_canonical="other",
        ),
        _block(
            "Figure 9. Occupancy predictions of OccAny and baselines on sequential data. We visualize predicted voxels and highlight class-wise gains.",
            page_no=17,
            section_title="Qualitative Examples",
            section_canonical="other",
        ),
        _block(
            "Figure 10. Occupancy predictions of OccAny and baselines on surround-view data. Compared to baselines, our predictions are denser and more accurate.",
            page_no=18,
            section_title="Qualitative Examples",
            section_canonical="other",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    summary = result.sections[0].summary_paragraph
    assert "sequential data" in summary
    assert "surround-view data" in summary


def test_build_section_overview_trims_tabular_prefix_before_prose(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "Eager OOM 99.2 99.2 Fused OOM 98.4 98.4 The following figures show single-layer end-to-end speedup and explain why model-level gains compound.",
            page_no=26,
            section_title="Results",
            section_canonical="results",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    summary = result.sections[0].summary_paragraph
    assert summary.startswith("The following figures show")
    assert "Eager OOM 99.2" not in summary


def test_build_section_overview_penalizes_result_sentences_in_related_work(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "These results suggest that our method improves retrieval on a benchmark and motivates the ablation study.",
            page_no=11,
            section_title="Related Work",
            section_canonical="related_work",
        ),
        _block(
            "Recent diffusion-based language models and trajectory-aware training methods explicitly target the training-inference discrepancy in diffusion decoding.",
            page_no=12,
            section_title="Related Work",
            section_canonical="related_work",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    summary = result.sections[0].summary_paragraph
    assert "Recent diffusion-based language models" in summary
    assert "ablation study" not in summary


def test_build_section_overview_trims_tabular_suffix_after_prose(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    blocks = [
        _block(
            "Our work introduces a novel framework for occupancy prediction prioritizing scalability and generalization. OccAny Distilled 623M 512x160 7.28 13.53 512x288 6.66 10.32 OccAny+ Distilled 651M 512x160 6.48 13.30 512x288 7.20 11.50",
            page_no=9,
            section_title="Conclusion",
            section_canonical="conclusion",
        ),
    ]

    result = build_section_overview(pdf_path, blocks=blocks, config=SectionOverviewConfig())

    summary = result.sections[0].summary_paragraph
    assert summary == "Our work introduces a novel framework for occupancy prediction prioritizing scalability and generalization."
