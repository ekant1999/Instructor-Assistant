from __future__ import annotations

from pathlib import Path

import pytest

from ia_phase1.figures import (
    _assign_captions_to_regions,
    _build_vector_region_from_caption,
    _cluster_embedded_bboxes,
    _infer_section_for_image,
    _merge_caption_adjacent_embedded_regions,
    _parse_figure_caption,
    _score_figure_region_for_caption,
    _recover_unassigned_embedded_captions,
    _resolve_page_figure_candidates,
    _trim_embedded_region_away_from_captions,
    extract_and_store_paper_figures,
    load_paper_figure_manifest,
    resolve_figure_file,
)
from ia_phase1.parser import extract_text_blocks


def test_extract_figures_from_text_only_pdf(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("FIGURE_VECTOR_ENABLED", "false")
    blocks = extract_text_blocks(sample_pdf)

    payload = extract_and_store_paper_figures(sample_pdf, paper_id=31, blocks=blocks)
    assert payload["paper_id"] == 31
    assert payload["num_images"] == 0

    manifest = load_paper_figure_manifest(31)
    assert manifest["num_images"] == 0
    assert manifest["images"] == []


def test_load_figure_manifest_missing_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path))
    payload = load_paper_figure_manifest(404)
    assert payload["paper_id"] == 404
    assert payload["num_images"] == 0
    assert payload["images"] == []


def test_resolve_figure_file_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        resolve_figure_file(1, "../escape.png")


def test_build_vector_region_from_caption_clips_margin_to_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_VECTOR_MIN_DRAWING_COUNT", "1")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_AREA_PT", "100")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_SIDE_PT", "10")
    monkeypatch.setenv("FIGURE_VECTOR_MARGIN_PT", "8")

    caption = {
        "text": "Figure 1: Demo",
        "bbox": {"x0": 120.0, "y0": 100.0, "x1": 260.0, "y1": 112.0},
    }
    candidate = _build_vector_region_from_caption(
        caption=caption,
        caption_index=0,
        captions=[caption],
        drawing_bboxes=[{"x0": 110.0, "y0": 60.0, "x1": 220.0, "y1": 95.0}],
        text_boxes=[],
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 400.0, "y1": 400.0},
    )

    assert candidate is not None
    assert candidate["bbox"]["y1"] <= 98.0


def test_build_vector_region_from_caption_expands_to_keep_nearby_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_VECTOR_MIN_DRAWING_COUNT", "1")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_AREA_PT", "100")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_SIDE_PT", "10")
    monkeypatch.setenv("FIGURE_VECTOR_MARGIN_PT", "0")
    monkeypatch.setenv("FIGURE_VECTOR_LABEL_MAX_GAP_PT", "18")

    caption = {
        "text": "Figure 1: Demo",
        "bbox": {"x0": 120.0, "y0": 220.0, "x1": 260.0, "y1": 232.0},
    }
    candidate = _build_vector_region_from_caption(
        caption=caption,
        caption_index=0,
        captions=[caption],
        drawing_bboxes=[{"x0": 100.0, "y0": 100.0, "x1": 200.0, "y1": 200.0}],
        text_boxes=[{"text": "Decoder", "bbox": {"x0": 203.0, "y0": 132.0, "x1": 248.0, "y1": 146.0}}],
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 400.0, "y1": 400.0},
    )

    assert candidate is not None
    assert candidate["bbox"]["x1"] >= 248.0


def test_build_vector_region_from_caption_trims_partial_prose_at_top_edge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_VECTOR_MIN_DRAWING_COUNT", "1")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_AREA_PT", "100")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_SIDE_PT", "10")
    monkeypatch.setenv("FIGURE_VECTOR_MARGIN_PT", "6")
    monkeypatch.setenv("FIGURE_VECTOR_TEXT_EDGE_BAND_PT", "20")

    caption = {
        "text": "Figure 4: Demo chart",
        "bbox": {"x0": 120.0, "y0": 500.0, "x1": 300.0, "y1": 512.0},
        "block_bbox": {"x0": 120.0, "y0": 500.0, "x1": 340.0, "y1": 530.0},
    }
    candidate = _build_vector_region_from_caption(
        caption=caption,
        caption_index=0,
        captions=[caption],
        drawing_bboxes=[{"x0": 100.0, "y0": 220.0, "x1": 340.0, "y1": 460.0}],
        text_boxes=[
            {"text": "Qwen3-VL-32B", "bbox": {"x0": 165.1, "y0": 205.4, "x1": 232.1, "y1": 215.3}},
            {"text": "512", "bbox": {"x0": 244.1, "y0": 205.7, "x1": 259.0, "y1": 215.6}},
            {"text": "1.70×", "bbox": {"x0": 284.4, "y0": 205.7, "x1": 309.8, "y1": 215.6}},
            {"text": "1.82×", "bbox": {"x0": 332.2, "y0": 205.7, "x1": 357.6, "y1": 215.6}},
            {"text": "1.16×", "bbox": {"x0": 380.4, "y0": 205.7, "x1": 405.9, "y1": 215.6}},
            {"text": "1.12×", "bbox": {"x0": 420.5, "y0": 205.7, "x1": 445.9, "y1": 215.6}},
            {"text": "768", "bbox": {"x0": 244.1, "y0": 219.1, "x1": 259.0, "y1": 229.0}},
            {"text": "1.74×", "bbox": {"x0": 284.4, "y0": 219.1, "x1": 309.8, "y1": 229.0}},
            {"text": "1.87×", "bbox": {"x0": 332.2, "y0": 219.1, "x1": 357.6, "y1": 229.0}},
            {"text": "1.14×", "bbox": {"x0": 380.4, "y0": 219.1, "x1": 405.9, "y1": 229.0}},
            {"text": "1.10×", "bbox": {"x0": 420.5, "y0": 219.1, "x1": 445.9, "y1": 229.0}},
            {"text": "Dense-BA Position: 0% = Eager, 100% = Fully Fused (Grad Compute)", "bbox": {"x0": 120.0, "y0": 250.0, "x1": 420.0, "y1": 265.0}},
        ],
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 600.0, "y1": 800.0},
    )

    assert candidate is not None
    assert candidate["bbox"]["y0"] >= 232.0


def test_build_vector_region_from_caption_keeps_right_column_chart_out_of_left_column_prose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_VECTOR_MIN_DRAWING_COUNT", "1")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_AREA_PT", "100")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_SIDE_PT", "10")
    monkeypatch.setenv("FIGURE_VECTOR_MARGIN_PT", "6")

    caption = {
        "text": "Figure 5: Comparison across context lengths.",
        "bbox": {"x0": 330.0, "y0": 628.0, "x1": 505.0, "y1": 639.0},
        "block_bbox": {"x0": 330.0, "y0": 628.0, "x1": 505.0, "y1": 660.0},
    }
    candidate = _build_vector_region_from_caption(
        caption=caption,
        caption_index=0,
        captions=[caption],
        drawing_bboxes=[
            {"x0": 108.0, "y0": 246.7, "x1": 504.0, "y1": 262.5},
            {"x0": 329.8, "y0": 512.9, "x1": 504.0, "y1": 621.6},
        ],
        text_boxes=[
            {
                "text": "MemDLM more directly. Across both backbones,",
                "bbox": {"x0": 108.0, "y0": 508.9, "x1": 321.0, "y1": 521.0},
            },
            {
                "text": "MemDLM descends more rapidly in training loss and",
                "bbox": {"x0": 108.0, "y0": 522.0, "x1": 321.0, "y1": 534.0},
            },
            {
                "text": "also maintains lower evaluation loss throughout train-",
                "bbox": {"x0": 108.0, "y0": 535.0, "x1": 321.0, "y1": 547.0},
            },
            {
                "text": "ing. This pattern is consistent with our interpretation",
                "bbox": {"x0": 108.0, "y0": 548.0, "x1": 321.0, "y1": 560.0},
            },
            {
                "text": "that Bi-level Optimization with fast weights improves",
                "bbox": {"x0": 108.0, "y0": 561.0, "x1": 321.0, "y1": 573.0},
            },
            {"text": "Pretrained vs. Trained", "bbox": {"x0": 398.2, "y0": 514.8, "x1": 449.6, "y1": 521.6}},
            {"text": "Score", "bbox": {"x0": 331.7, "y0": 558.0, "x1": 338.1, "y1": 570.9}},
            {"text": "1K 2K 4K 8K 16K 32K Context length", "bbox": {"x0": 351.2, "y0": 606.7, "x1": 497.8, "y1": 619.1}},
        ],
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 612.0, "y1": 792.0},
    )

    assert candidate is not None
    assert candidate["bbox"]["x0"] >= 320.0
    assert candidate["bbox"]["x1"] <= 511.0


def test_build_vector_region_from_caption_ignores_previous_caption_in_other_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_VECTOR_MIN_DRAWING_COUNT", "1")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_AREA_PT", "5000")
    monkeypatch.setenv("FIGURE_VECTOR_MIN_REGION_SIDE_PT", "10")
    monkeypatch.setenv("FIGURE_VECTOR_MARGIN_PT", "6")

    right_caption = {
        "text": "Figure 8: Right-column chart.",
        "bbox": {"x0": 320.0, "y0": 347.0, "x1": 540.0, "y1": 359.0},
        "block_bbox": {"x0": 317.0, "y0": 347.0, "x1": 545.0, "y1": 370.0},
    }
    left_caption = {
        "text": "Figure 6: Left-column chart.",
        "bbox": {"x0": 78.0, "y0": 378.0, "x1": 255.0, "y1": 390.0},
        "block_bbox": {"x0": 76.0, "y0": 377.0, "x1": 260.0, "y1": 400.0},
    }
    candidate = _build_vector_region_from_caption(
        caption=left_caption,
        caption_index=1,
        captions=[right_caption, left_caption],
        drawing_bboxes=[{"x0": 95.0, "y0": 273.0, "x1": 255.0, "y1": 370.0}],
        text_boxes=[],
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 612.0, "y1": 792.0},
    )

    assert candidate is not None
    assert candidate["bbox"]["x1"] < 300.0
    assert candidate["bbox"]["y0"] < 320.0


def test_parse_figure_caption_requires_explicit_caption_punctuation() -> None:
    parsed = _parse_figure_caption("Figure 6: Representation alignment between tokenization and generation pathways.")
    assert parsed == {
        "label": "Figure",
        "number": "6",
        "body": "Representation alignment between tokenization and generation pathways.",
        "text": "Figure 6: Representation alignment between tokenization and generation pathways.",
    }
    assert _parse_figure_caption("Figure 9 and Table 7 show both theoretical and measured memory reductions.") is None


def test_cluster_embedded_bboxes_groups_adjacent_tiles() -> None:
    clusters = _cluster_embedded_bboxes(
        [
            {"x0": 10.0, "y0": 10.0, "x1": 40.0, "y1": 40.0},
            {"x0": 40.5, "y0": 10.0, "x1": 70.0, "y1": 40.0},
            {"x0": 10.0, "y0": 40.5, "x1": 40.0, "y1": 70.0},
            {"x0": 200.0, "y0": 200.0, "x1": 240.0, "y1": 240.0},
        ]
    )
    cluster_sizes = sorted(len(cluster) for cluster in clusters)
    assert cluster_sizes == [1, 3]


def test_assign_captions_to_regions_uses_best_region() -> None:
    regions = [
        {"bbox": {"x0": 40.0, "y0": 20.0, "x1": 180.0, "y1": 120.0}},
        {"bbox": {"x0": 260.0, "y0": 30.0, "x1": 360.0, "y1": 110.0}},
    ]
    captions = [
        {
            "text": "Figure 3: Demo figure",
            "bbox": {"x0": 60.0, "y0": 130.0, "x1": 190.0, "y1": 144.0},
            "block_bbox": {"x0": 50.0, "y0": 128.0, "x1": 210.0, "y1": 148.0},
            "figure_label": "Figure",
            "figure_number": "3",
            "figure_body": "Demo figure",
        }
    ]

    _assign_captions_to_regions(regions=regions, captions=captions)

    assert regions[0]["figure_number"] == "3"
    assert regions[0]["figure_body"] == "Demo figure"
    assert "figure_number" not in regions[1]


def test_assign_captions_to_regions_relaxed_single_remaining_match() -> None:
    regions = [
        {"bbox": {"x0": 40.0, "y0": 40.0, "x1": 360.0, "y1": 220.0}},
    ]
    captions = [
        {
            "text": "Figure 10. Surround-view qualitative results.",
            "bbox": {"x0": 28.0, "y0": 228.0, "x1": 240.0, "y1": 240.0},
            "block_bbox": {"x0": 28.0, "y0": 226.0, "x1": 420.0, "y1": 246.0},
            "figure_label": "Figure",
            "figure_number": "10",
            "figure_body": "Surround-view qualitative results.",
        }
    ]

    _assign_captions_to_regions(regions=regions, captions=captions)

    assert regions[0]["figure_number"] == "10"
    assert regions[0]["figure_body"] == "Surround-view qualitative results."


def test_trim_embedded_region_away_from_overlapping_caption_bottom_edge() -> None:
    region_bbox = {"x0": 70.0, "y0": 95.0, "x1": 606.0, "y1": 658.0}
    captions = [
        {
            "text": "Figure 10. Occupancy predictions.",
            "bbox": {"x0": 58.0, "y0": 640.0, "x1": 553.0, "y1": 652.0},
            "block_bbox": {"x0": 58.0, "y0": 640.0, "x1": 553.0, "y1": 662.0},
            "figure_label": "Figure",
            "figure_number": "10",
            "figure_body": "Occupancy predictions.",
        }
    ]

    trimmed = _trim_embedded_region_away_from_captions(
        region_bbox=region_bbox,
        captions=captions,
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 612.0, "y1": 792.0},
    )

    assert trimmed is not None
    assert trimmed["y1"] < 640.0


def test_recover_unassigned_embedded_captions_from_trimmed_large_region() -> None:
    regions = [
        {
            "bbox": {"x0": 73.0, "y0": 95.0, "x1": 606.0, "y1": 636.0},
            "tile_count": 70,
        }
    ]
    captions = [
        {
            "text": "Figure 10. Occupancy predictions of OccAny and baselines on surround-view data.",
            "bbox": {"x0": 58.0, "y0": 640.0, "x1": 553.0, "y1": 652.0},
            "block_bbox": {"x0": 58.0, "y0": 640.0, "x1": 553.0, "y1": 662.0},
            "figure_label": "Figure",
            "figure_number": "10",
            "figure_body": "Occupancy predictions of OccAny and baselines on surround-view data.",
        }
    ]

    _recover_unassigned_embedded_captions(regions=regions, captions=captions)

    assert regions[0]["figure_number"] == "10"
    assert regions[0]["figure_body"] == "Occupancy predictions of OccAny and baselines on surround-view data."


def test_resolve_page_figure_candidates_keeps_best_same_number_and_removes_loser(
    tmp_path: Path,
) -> None:
    loser_path = tmp_path / "page_007_vec_001.png"
    winner_path = tmp_path / "page_007_img_001.png"
    loser_path.write_bytes(b"loser")
    winner_path.write_bytes(b"winner")

    kept = _resolve_page_figure_candidates(
        [
            {
                "page_no": 7,
                "file_name": loser_path.name,
                "image_path": str(loser_path),
                "figure_number": "5",
                "figure_type": "vector",
                "bbox": {"x0": 320.0, "y0": 336.0, "x1": 558.0, "y1": 414.0},
                "_candidate_score": 4.0,
            },
            {
                "page_no": 7,
                "file_name": winner_path.name,
                "image_path": str(winner_path),
                "figure_number": "5",
                "figure_type": "embedded",
                "bbox": {"x0": 80.0, "y0": 49.0, "x1": 606.0, "y1": 294.0},
                "_candidate_score": 8.5,
            },
        ]
    )

    assert len(kept) == 1
    assert kept[0]["figure_type"] == "embedded"
    assert winner_path.exists()
    assert not loser_path.exists()


def test_merge_caption_adjacent_embedded_regions_combines_split_composite_figure() -> None:
    captions = [
        {
            "text": "Figure 1. Demo figure.",
            "bbox": {"x0": 317.25, "y0": 313.59, "x1": 553.50, "y1": 325.26},
            "block_bbox": {"x0": 317.25, "y0": 313.59, "x1": 554.99, "y1": 357.60},
            "figure_label": "Figure",
            "figure_number": "1",
            "figure_body": "Demo figure.",
        }
    ]
    regions = [
        {
            "bbox": {"x0": 413.56, "y0": 181.51, "x1": 612.0, "y1": 309.59},
            "tile_count": 6,
        },
        {
            "bbox": {"x0": 324.78, "y0": 264.41, "x1": 378.50, "y1": 304.71},
            "tile_count": 5,
            "figure_caption": captions[0]["text"],
            "figure_label": "Figure",
            "figure_number": "1",
            "figure_body": "Demo figure.",
            "caption_bbox": captions[0]["bbox"],
            "caption_block_bbox": captions[0]["block_bbox"],
        },
    ]

    _merge_caption_adjacent_embedded_regions(
        regions=regions,
        captions=captions,
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 612.0, "y1": 792.0},
    )

    assert len(regions) == 1
    assert regions[0]["figure_number"] == "1"
    assert regions[0]["tile_count"] == 11
    assert regions[0]["bbox"]["x0"] <= 325.0
    assert regions[0]["bbox"]["x1"] >= 611.0


def test_score_figure_region_for_caption_penalizes_tiny_vector_fragment_against_wider_caption() -> None:
    caption_bbox = {"x0": 317.25, "y0": 313.59, "x1": 554.99, "y1": 357.60}
    vector_score = _score_figure_region_for_caption(
        bbox={"x0": 489.07, "y0": 223.76, "x1": 555.88, "y1": 301.27},
        caption_bbox=caption_bbox,
        kind="vector",
        density_count=10,
        base_score=2.8845,
    )
    embedded_score = _score_figure_region_for_caption(
        bbox={"x0": 324.78, "y0": 181.51, "x1": 612.0, "y1": 309.59},
        caption_bbox=caption_bbox,
        kind="embedded",
        density_count=11,
    )

    assert embedded_score > vector_score


def test_infer_section_for_image_prefers_caption_column_narrative_over_figure_label_noise() -> None:
    page_blocks = [
        {
            "text": "Sequence/Monocular 3D Occupancy Segmentation",
            "bbox": {"x0": 318.0, "y0": 223.0, "x1": 554.0, "y1": 250.0},
            "section_canonical": "abstract",
            "section_title": "Abstract",
            "section_source": "heuristic",
            "section_confidence": 0.9,
        },
        {
            "text": "Relying on in-domain annotations and precise sensor-rig priors, existing 3D occupancy prediction methods are limited.",
            "bbox": {"x0": 58.0, "y0": 250.0, "x1": 295.0, "y1": 360.0},
            "section_canonical": "abstract",
            "section_title": "Abstract",
            "section_source": "heuristic",
            "section_confidence": 0.9,
        },
        {
            "text": "and dataset [4, 10, 13, 18], current state-of-the-art 3D models still lack the generalization of human perception.",
            "bbox": {"x0": 316.0, "y0": 376.0, "x1": 554.0, "y1": 450.0},
            "section_canonical": "introduction",
            "section_title": "Introduction",
            "section_source": "pdf_toc",
            "section_confidence": 0.98,
        },
    ]
    section = _infer_section_for_image(
        page_blocks,
        {"x0": 324.7, "y0": 181.5, "x1": 612.0, "y1": 309.6},
        caption_bbox={"x0": 317.2, "y0": 313.6, "x1": 555.0, "y1": 357.6},
    )

    assert section["section_canonical"] == "introduction"
