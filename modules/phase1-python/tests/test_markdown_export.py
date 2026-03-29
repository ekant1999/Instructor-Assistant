from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ia_phase1.markdown_export import MarkdownExportConfig, export_pdf_to_markdown


def test_export_pdf_to_markdown_writes_bundle_and_positions_assets(
    sample_pdf: Path,
    sectioned_blocks,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 55
    working_blocks = deepcopy(sectioned_blocks)
    working_blocks.extend(
        [
            {
                "text": "_compose_with_dispatch",
                "page_no": 1,
                "block_index": 99,
                "bbox": {"x0": 5.0, "y0": 46.0, "x1": 75.0, "y1": 48.0},
                "metadata": {
                    "section_canonical": "introduction",
                    "section_title": "Introduction",
                    "section_source": "heuristic",
                    "section_confidence": 0.85,
                },
            },
            {
                "text": "# [d_in , d_in]",
                "page_no": 2,
                "block_index": 100,
                "bbox": {"x0": 5.0, "y0": 18.0, "x1": 75.0, "y1": 22.0},
                "metadata": {
                    "section_canonical": "methodology",
                    "section_title": "Method",
                    "section_source": "heuristic",
                    "section_confidence": 0.9,
                },
            },
            {
                "text": "Figure 1: Pipeline figure",
                "page_no": 1,
                "block_index": 101,
                "bbox": {"x0": 0.0, "y0": 52.0, "x1": 95.0, "y1": 58.0},
                "metadata": {
                    "section_canonical": "introduction",
                    "section_title": "Introduction",
                    "section_source": "heuristic",
                    "section_confidence": 0.85,
                },
            },
        ]
    )
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))

    figure_dir = tmp_path / "figures" / str(paper_id)
    table_dir = tmp_path / "tables" / str(paper_id)
    equation_dir = tmp_path / "equations" / str(paper_id)
    for path in (figure_dir, table_dir, equation_dir):
        path.mkdir(parents=True, exist_ok=True)

    (figure_dir / "page_001_img_001.png").write_bytes(b"\x89PNG\r\n\x1a\nfigure")
    (table_dir / "table_0001.json").write_text(
        json.dumps({"id": 1, "rows": [["a", "b"]]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (equation_dir / "equation_0001.png").write_bytes(b"\x89PNG\r\n\x1a\nequation")
    (equation_dir / "equation_0001.json").write_text(
        json.dumps({"id": 1, "text": "x = y + z"}, ensure_ascii=False),
        encoding="utf-8",
    )

    (figure_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_images": 1,
                "images": [
                    {
                        "id": 8,
                        "page_no": 1,
                        "file_name": "page_001_img_001.png",
                        "figure_caption": "Figure 1: Pipeline figure",
                        "figure_number": "1",
                        "figure_body": "Pipeline figure",
                        "figure_type": "embedded",
                        "section_canonical": "introduction",
                        "section_title": "Introduction",
                        "bbox": {"x0": 0.0, "y0": 45.0, "x1": 80.0, "y1": 49.0},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (table_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_tables": 1,
                "tables": [
                    {
                        "id": 1,
                        "page_no": 2,
                        "json_file": "table_0001.json",
                        "caption": "Results table",
                        "section_canonical": "methodology",
                        "section_title": "Method",
                        "bbox": {"x0": 0.0, "y0": 45.0, "x1": 80.0, "y1": 49.0},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (equation_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_equations": 1,
                "equations": [
                    {
                        "id": 1,
                        "equation_number": "1",
                        "page_no": 2,
                        "file_name": "equation_0001.png",
                        "json_file": "equation_0001.json",
                        "latex": "x = y + z",
                        "latex_source": "text_fallback",
                        "latex_confidence": 0.46,
                        "render_mode": "latex",
                        "section_canonical": "methodology",
                        "section_title": "Method",
                        "bbox": {"x0": 0.0, "y0": 60.0, "x1": 80.0, "y1": 64.0},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_bundle",
        blocks=working_blocks,
        source_url="https://example.test/paper",
        metadata={"title": "Exported Sample"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    assert result.markdown_path.exists()
    assert result.manifest_path.exists()
    assert (result.bundle_dir / "assets" / "figures" / "page_001_img_001.png").exists()
    assert (result.bundle_dir / "assets" / "tables" / "table_0001.json").exists()
    assert (result.bundle_dir / "assets" / "equations" / "equation_0001.json").exists()
    assert (result.bundle_dir / "assets" / "equations" / "equation_0001.png").exists()

    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert "title: \"Exported Sample\"" in markdown
    assert "![Figure 1](assets/figures/page_001_img_001.png)" in markdown
    assert "![Figure 1](assets/figures/page_001_img_001.png)\n\n_Figure 1: Pipeline figure_" in markdown
    assert "_compose_with_dispatch" not in markdown
    assert markdown.count("Pipeline figure") == 1
    assert "_Figure 1: Figure 1: Pipeline figure_" not in markdown
    assert "> Table JSON: `assets/tables/table_0001.json`" in markdown
    assert "> Table 1: Results table" in markdown
    assert "| a | b |" not in markdown
    assert "\n\\# [d_in , d_in]\n" in markdown
    assert "\n# [d_in , d_in]\n" not in markdown
    assert "$$\nx = y + z\n$$" in markdown
    assert "> Equation 1 JSON: `assets/equations/equation_0001.json`" in markdown
    assert "> Equation 1 image: `assets/equations/equation_0001.png`" in markdown
    assert "![Equation 1](assets/equations/equation_0001.png)" not in markdown

    figure_pos = markdown.index("assets/figures/page_001_img_001.png")
    table_pos = markdown.index("assets/tables/table_0001.json")
    table_caption_pos = markdown.index("> Table 1: Results table")
    latex_pos = markdown.index("x = y + z")
    equation_pos = markdown.index("assets/equations/equation_0001.json")
    equation_image_pos = markdown.index("assets/equations/equation_0001.png")
    method_pos = markdown.index("Method text block")

    assert figure_pos < method_pos
    assert method_pos < table_pos < table_caption_pos < latex_pos < equation_pos < equation_image_pos

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["asset_counts"] == {"figures": 1, "tables": 1, "equations": 1}
    assert manifest["assets"]["tables"][0]["markdown_json_path"] == "assets/tables/table_0001.json"
    assert manifest["assets"]["equations"][0]["latex"] == "x = y + z"


def test_export_pdf_to_markdown_filters_page_furniture_and_bad_assets(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 77
    blocks = [
        {
            "text": "Sample Document Title",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 5.0, "x1": 110.0, "y1": 14.0},
            "metadata": {
                "first_line": "Sample Document Title",
                "section_canonical": "front_matter",
                "section_title": "Front Matter",
                "section_source": "heuristic",
                "section_confidence": 0.4,
            },
        },
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 24.0, "x1": 80.0, "y1": 34.0},
            "metadata": {
                "first_line": "Abstract",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Clean abstract text.",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 10.0, "y0": 40.0, "x1": 180.0, "y1": 65.0},
            "metadata": {
                "first_line": "Clean abstract text.",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Author One\nAuthor Two",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 90.0, "y0": 15.0, "x1": 170.0, "y1": 28.0},
            "metadata": {
                "first_line": "Author One",
                "section_canonical": "front_matter",
                "section_title": "Front Matter",
                "section_source": "heuristic",
                "section_confidence": 0.4,
                "line_count": 2,
                "char_count": 21,
            },
        },
        {
            "text": (
                "This abstract paragraph references a public github.com/example/project repository as part of the narrative "
                "and should remain in the markdown because it is body prose rather than front-matter metadata. " * 2
            ).strip(),
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 10.0, "y0": 66.0, "x1": 220.0, "y1": 110.0},
            "metadata": {
                "first_line": "This abstract paragraph references a public github.com/example/project repository as part of the narrative",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
                "line_count": 5,
                "char_count": 280,
            },
        },
        {
            "text": "1",
            "page_no": 1,
            "block_index": 5,
            "bbox": {"x0": 95.0, "y0": 190.0, "x1": 105.0, "y1": 198.0},
            "metadata": {
                "first_line": "1",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Prompt",
            "page_no": 1,
            "block_index": 6,
            "bbox": {"x0": 45.0, "y0": 78.0, "x1": 78.0, "y1": 88.0},
            "metadata": {
                "first_line": "Prompt",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Sample Document Title",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 5.0, "x1": 110.0, "y1": 14.0},
            "metadata": {
                "first_line": "Sample Document Title",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Method text block",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 30.0, "x1": 180.0, "y1": 60.0},
            "metadata": {
                "first_line": "Method text block",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Surround",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 150.0, "y0": 82.0, "x1": 190.0, "y1": 92.0},
            "metadata": {
                "first_line": "Surround",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Figure 1. A useful fi-\ngure",
            "page_no": 2,
            "block_index": 2,
            "bbox": {"x0": 10.0, "y0": 132.0, "x1": 160.0, "y1": 145.0},
            "metadata": {
                "first_line": "Figure 1. A useful fi-",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "arXiv:2603.22283v1 [cs.CV] 23 Mar 2026",
            "page_no": 2,
            "block_index": 3,
            "bbox": {"x0": 2.0, "y0": 120.0, "x1": 35.0, "y1": 180.0},
            "metadata": {
                "first_line": "arXiv:2603.22283v1 [cs.CV] 23 Mar 2026",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Code: https://github.com/example/project",
            "page_no": 1,
            "block_index": 7,
            "bbox": {"x0": 10.0, "y0": 80.0, "x1": 160.0, "y1": 95.0},
            "metadata": {
                "first_line": "Code: https://github.com/example/project",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "*Equal contribution 1 Example University 2 Example Lab.",
            "page_no": 1,
            "block_index": 8,
            "bbox": {"x0": 10.0, "y0": 96.0, "x1": 190.0, "y1": 108.0},
            "metadata": {
                "first_line": "*Equal contribution 1 Example University 2 Example Lab.",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
        {
            "text": "Example Lab, Paris, France",
            "page_no": 1,
            "block_index": 9,
            "bbox": {"x0": 90.0, "y0": 112.0, "x1": 180.0, "y1": 124.0},
            "metadata": {
                "first_line": "Example Lab, Paris, France",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.9,
                "line_count": 1,
                "char_count": 25,
            },
        },
        {
            "text": "■car ■road ■person",
            "page_no": 2,
            "block_index": 10,
            "bbox": {"x0": 16.0, "y0": 96.0, "x1": 180.0, "y1": 108.0},
            "metadata": {
                "first_line": "■car ■road ■person",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setenv("MARKDOWN_MAX_EMBEDDED_IMAGES_PER_PAGE", "3")

    figure_dir = tmp_path / "figures" / str(paper_id)
    table_dir = tmp_path / "tables" / str(paper_id)
    equation_dir = tmp_path / "equations" / str(paper_id)
    for path in (figure_dir, table_dir, equation_dir):
        path.mkdir(parents=True, exist_ok=True)

    for idx in range(1, 5):
        (figure_dir / f"page_001_img_{idx:03d}.png").write_bytes(b"\x89PNG\r\n\x1a\nimg")
    (figure_dir / "page_002_vec_001.png").write_bytes(b"\x89PNG\r\n\x1a\nvec")
    (figure_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_images": 5,
                "images": [
                    {
                        "id": 1,
                        "page_no": 1,
                        "file_name": "page_001_img_001.png",
                        "figure_type": "embedded",
                        "figure_caption": "",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 5.0, "y0": 70.0, "x1": 35.0, "y1": 95.0},
                    },
                    {
                        "id": 2,
                        "page_no": 1,
                        "file_name": "page_001_img_002.png",
                        "figure_type": "embedded",
                        "figure_caption": "",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 40.0, "y0": 70.0, "x1": 70.0, "y1": 95.0},
                    },
                    {
                        "id": 3,
                        "page_no": 1,
                        "file_name": "page_001_img_003.png",
                        "figure_type": "embedded",
                        "figure_caption": "",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 75.0, "y0": 70.0, "x1": 105.0, "y1": 95.0},
                    },
                    {
                        "id": 4,
                        "page_no": 1,
                        "file_name": "page_001_img_004.png",
                        "figure_type": "embedded",
                        "figure_caption": "",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 110.0, "y0": 70.0, "x1": 140.0, "y1": 95.0},
                    },
                    {
                        "id": 5,
                        "page_no": 2,
                        "file_name": "page_002_vec_001.png",
                        "figure_type": "vector",
                        "figure_caption": "Figure 1. A useful figure",
                        "figure_number": "1",
                        "section_canonical": "methodology",
                        "section_title": "Method",
                        "bbox": {"x0": 10.0, "y0": 75.0, "x1": 140.0, "y1": 130.0},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (table_dir / "table_0001.json").write_text(json.dumps({"id": 1}, ensure_ascii=False), encoding="utf-8")
    (table_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_tables": 1,
                "tables": [
                    {
                        "id": 1,
                        "page_no": 2,
                        "json_file": "table_0001.json",
                        "caption": "",
                        "n_rows": 1,
                        "headers": ["Very long header", "Another header"],
                        "rows": [["This is not a real table row and should be suppressed because it is too long.", ""]],
                        "section_canonical": "methodology",
                        "section_title": "Method",
                        "bbox": {"x0": 10.0, "y0": 132.0, "x1": 180.0, "y1": 165.0},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (equation_dir / "equation_0001.png").write_bytes(b"\x89PNG\r\n\x1a\neq")
    (equation_dir / "equation_0001.json").write_text(json.dumps({"id": 1}, ensure_ascii=False), encoding="utf-8")
    (equation_dir / "equation_0002.png").write_bytes(b"\x89PNG\r\n\x1a\neq")
    (equation_dir / "equation_0002.json").write_text(json.dumps({"id": 2}, ensure_ascii=False), encoding="utf-8")
    (equation_dir / "equation_0003.png").write_bytes(b"\x89PNG\r\n\x1a\neq")
    (equation_dir / "equation_0003.json").write_text(json.dumps({"id": 3}, ensure_ascii=False), encoding="utf-8")
    (equation_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_equations": 3,
                "equations": [
                    {
                        "id": 1,
                        "equation_number": "1",
                        "page_no": 1,
                        "file_name": "equation_0001.png",
                        "json_file": "equation_0001.json",
                        "text": "https://github.com/example/project",
                        "latex": "\\begin{aligned}\nhttps://github.com/example/project\n\\end{aligned}",
                        "latex_source": "text_fallback",
                        "render_mode": "latex",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 10.0, "y0": 100.0, "x1": 140.0, "y1": 112.0},
                    },
                    {
                        "id": 2,
                        "equation_number": "2",
                        "page_no": 2,
                        "file_name": "equation_0002.png",
                        "json_file": "equation_0002.json",
                        "text": "x = y + z",
                        "latex": "x = y + z",
                        "latex_source": "text_fallback",
                        "render_mode": "latex",
                        "section_canonical": "methodology",
                        "section_title": "Method",
                        "bbox": {"x0": 10.0, "y0": 170.0, "x1": 80.0, "y1": 180.0},
                    },
                    {
                        "id": 3,
                        "equation_number": "3",
                        "page_no": 2,
                        "file_name": "equation_0003.png",
                        "json_file": "equation_0003.json",
                        "text": "⋆ Stage-1 only (L2+LPIPS+KL).",
                        "latex": "\\begin{aligned}\n⋆ Stage-1 only (L2+LPIPS+KL).\n\\end{aligned}",
                        "latex_source": "text_fallback",
                        "render_mode": "latex",
                        "section_canonical": "methodology",
                        "section_title": "Method",
                        "bbox": {"x0": 10.0, "y0": 182.0, "x1": 140.0, "y1": 192.0},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_filtered",
        blocks=blocks,
        metadata={"title": "Sample Document Title"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.count("Sample Document Title") == 1
    assert "\narXiv:" not in markdown
    assert "Code: https://github.com/example/project" not in markdown
    assert "Equal contribution" not in markdown
    assert "Example Lab, Paris, France" not in markdown
    assert "Author One" in markdown
    assert "Author Two" in markdown
    assert "\n1\n" not in markdown
    assert "This abstract paragraph references a public github.com/example/project repository" in markdown
    assert "assets/figures/page_001_img_001.png" not in markdown
    assert "assets/figures/page_002_vec_001.png" in markdown
    assert "■car ■road ■person" not in markdown
    assert "\nPrompt\n" not in markdown
    assert "\nSurround\n" not in markdown
    assert "\nFigure 1. A useful figure\n" not in markdown
    assert "assets/tables/table_0001.json" not in markdown
    assert "\nCode: https://github.com/example/project\n" not in markdown
    assert "Stage-1 only" not in markdown
    assert "$$\nx = y + z\n$$" in markdown


def test_export_pdf_to_markdown_realigns_asset_sections_and_skips_raw_heading_blocks(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 88
    blocks = [
        {
            "text": "Introduction",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 20.0, "x1": 120.0, "y1": 35.0},
            "metadata": {
                "first_line": "Introduction",
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
                "section_index": 1,
            },
        },
        {
            "text": "Intro body text.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 40.0, "x1": 200.0, "y1": 80.0},
            "metadata": {
                "first_line": "Intro body text.",
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
                "section_index": 1,
            },
        },
        {
            "text": "3.1. From VAE to UNITE",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 10.0, "y0": 120.0, "x1": 220.0, "y1": 140.0},
            "metadata": {
                "first_line": "3.1. From VAE to UNITE",
                "section_canonical": "from_vae_to_unite",
                "section_title": "From VAE to UNITE",
                "section_level": 2,
                "section_index": 2,
            },
        },
        {
            "text": "Method body text.",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 10.0, "y0": 150.0, "x1": 220.0, "y1": 190.0},
            "metadata": {
                "first_line": "Method body text.",
                "section_canonical": "from_vae_to_unite",
                "section_title": "From VAE to UNITE",
                "section_level": 2,
                "section_index": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))

    figure_dir = tmp_path / "figures" / str(paper_id)
    table_dir = tmp_path / "tables" / str(paper_id)
    equation_dir = tmp_path / "equations" / str(paper_id)
    for path in (figure_dir, table_dir, equation_dir):
        path.mkdir(parents=True, exist_ok=True)

    (equation_dir / "equation_0001.png").write_bytes(b"\x89PNG\r\n\x1a\neq")
    (equation_dir / "equation_0001.json").write_text(json.dumps({"id": 1}, ensure_ascii=False), encoding="utf-8")
    (equation_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_equations": 1,
                "equations": [
                    {
                        "id": 1,
                        "equation_number": "5",
                        "page_no": 1,
                        "file_name": "equation_0001.png",
                        "json_file": "equation_0001.json",
                        "text": "x = y + z",
                        "latex": "x = y + z",
                        "latex_source": "text_fallback",
                        "render_mode": "latex",
                        "section_canonical": "related_work",
                        "section_title": "Related Work",
                        "bbox": {"x0": 10.0, "y0": 175.0, "x1": 120.0, "y1": 190.0},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (figure_dir / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (table_dir / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_realign",
        blocks=blocks,
        metadata={"title": "Section Realign"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert "## Related Work" not in markdown
    assert markdown.count("## From VAE to UNITE") == 1
    assert markdown.count("3.1. From VAE to UNITE") == 0
    assert "$$\nx = y + z\n$$" in markdown


def test_export_pdf_to_markdown_skips_inferred_table_regions_without_hijacking_sections(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 89
    blocks = [
        {
            "text": "4. Analysis",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 20.0, "x1": 120.0, "y1": 35.0},
            "metadata": {
                "first_line": "4. Analysis",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Analysis intro paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 40.0, "x1": 240.0, "y1": 70.0},
            "metadata": {
                "first_line": "Analysis intro paragraph.",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Table 1. Benchmark comparison.",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 10.0, "y0": 90.0, "x1": 220.0, "y1": 105.0},
            "metadata": {
                "first_line": "Table 1. Benchmark comparison.",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Method Aux. Params FID↓ IS↑",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 10.0, "y0": 110.0, "x1": 220.0, "y1": 122.0},
            "metadata": {
                "first_line": "Method Aux. Params FID↓ IS↑",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "UNITE-B Joint 217M 2.12 294.1",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 10.0, "y0": 126.0, "x1": 220.0, "y1": 138.0},
            "metadata": {
                "first_line": "UNITE-B Joint 217M 2.12 294.1",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "† Decoder-only ft, 16 epochs.",
            "page_no": 1,
            "block_index": 5,
            "bbox": {"x0": 10.0, "y0": 142.0, "x1": 190.0, "y1": 154.0},
            "metadata": {
                "first_line": "† Decoder-only ft, 16 epochs.",
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_level": 2,
                "section_index": 5,
            },
        },
        {
            "text": "5. Results",
            "page_no": 1,
            "block_index": 6,
            "bbox": {"x0": 10.0, "y0": 190.0, "x1": 120.0, "y1": 205.0},
            "metadata": {
                "first_line": "5. Results",
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "section_index": 6,
            },
        },
        {
            "text": "Results paragraph with actual prose content and enough detail to remain in the markdown output.",
            "page_no": 1,
            "block_index": 7,
            "bbox": {"x0": 10.0, "y0": 210.0, "x1": 260.0, "y1": 250.0},
            "metadata": {
                "first_line": "Results paragraph with actual prose content and enough detail to remain in the markdown output.",
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "section_index": 6,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    for folder in ("tables", "figures", "equations"):
        path = tmp_path / folder / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
        manifest_name = "manifest.json"
        if folder == "tables":
            payload = {"paper_id": paper_id, "num_tables": 0, "tables": []}
        elif folder == "figures":
            payload = {"paper_id": paper_id, "num_images": 0, "images": []}
        else:
            payload = {"paper_id": paper_id, "num_equations": 0, "equations": []}
        (path / manifest_name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_table_regions",
        blocks=blocks,
        metadata={"title": "Table Region Filter"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert "Table 1. Benchmark comparison." in markdown
    assert "Method Aux. Params FID" not in markdown
    assert "UNITE-B Joint 217M 2.12 294.1" not in markdown
    assert "Decoder-only ft" not in markdown
    assert markdown.count("## Analysis") == 1
    assert markdown.count("## Results") == 1


def test_export_pdf_to_markdown_preserves_source_block_order_for_two_column_layouts(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 90
    blocks = [
        {
            "text": "4. Analysis",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 20.0, "x1": 140.0, "y1": 35.0},
            "metadata": {
                "first_line": "4. Analysis",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Left-column analysis body that should stay before the next section heading.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 220.0, "x1": 230.0, "y1": 260.0},
            "metadata": {
                "first_line": "Left-column analysis body that should stay before the next section heading.",
                "section_canonical": "analysis",
                "section_title": "Analysis",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "5. Results",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 320.0, "y0": 120.0, "x1": 430.0, "y1": 135.0},
            "metadata": {
                "first_line": "5. Results",
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "section_index": 5,
            },
        },
        {
            "text": "Right-column results body.",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 320.0, "y0": 150.0, "x1": 500.0, "y1": 190.0},
            "metadata": {
                "first_line": "Right-column results body.",
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "section_index": 5,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    for folder in ("tables", "figures", "equations"):
        path = tmp_path / folder / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
        if folder == "tables":
            payload = {"paper_id": paper_id, "num_tables": 0, "tables": []}
        elif folder == "figures":
            payload = {"paper_id": paper_id, "num_images": 0, "images": []}
        else:
            payload = {"paper_id": paper_id, "num_equations": 0, "equations": []}
        (path / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_two_column_order",
        blocks=blocks,
        metadata={"title": "Two Column Order"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.count("## Analysis") == 1
    assert markdown.count("## Results") == 1
    assert markdown.index("Left-column analysis body") < markdown.index("## Results")


def test_export_pdf_to_markdown_preserves_front_matter_and_promotes_structural_heading_blocks(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 91
    blocks = [
        {
            "text": "Repeated Title",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 120.0, "y0": 84.0, "x1": 475.0, "y1": 110.0},
            "metadata": {
                "first_line": "Repeated Title",
                "line_count": 1,
                "char_count": 14,
                "max_font_size": 18.0,
                "layout_role": "column_block",
                "column_hint": "right",
                "section_canonical": "front_matter",
                "section_title": "Front Matter",
                "section_level": 1,
            },
        },
        {
            "text": "Alice Example 1, Bob Example 2, Carol Example 1",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 120.0, "y0": 136.0, "x1": 470.0, "y1": 150.0},
            "metadata": {
                "first_line": "Alice Example 1, Bob Example 2, Carol Example 1",
                "line_count": 2,
                "char_count": 46,
                "max_font_size": 10.0,
                "layout_role": "column_block",
                "column_hint": "left",
                "section_canonical": "front_matter",
                "section_title": "Front Matter",
                "section_level": 1,
            },
        },
        {
            "text": "1 Example University 2 Example Lab",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 160.0, "y0": 156.0, "x1": 420.0, "y1": 170.0},
            "metadata": {
                "first_line": "1 Example University 2 Example Lab",
                "line_count": 1,
                "char_count": 34,
                "max_font_size": 9.0,
                "layout_role": "column_block",
                "column_hint": "right",
                "section_canonical": "front_matter",
                "section_title": "Front Matter",
                "section_level": 1,
            },
        },
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 285.0, "y0": 214.0, "x1": 330.0, "y1": 228.0},
            "metadata": {
                "first_line": "Abstract",
                "line_count": 1,
                "char_count": 8,
                "max_font_size": 12.0,
                "layout_role": "column_block",
                "column_hint": "right",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "This abstract body should remain under the abstract heading and before the introduction heading appears.",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 145.0, "y0": 240.0, "x1": 470.0, "y1": 320.0},
            "metadata": {
                "first_line": "This abstract body should remain under the abstract heading and before the introduction heading appears.",
                "line_count": 4,
                "char_count": 96,
                "max_font_size": 10.0,
                "layout_role": "column_block",
                "column_hint": "right",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "1 Introduction",
            "page_no": 1,
            "block_index": 5,
            "bbox": {"x0": 80.0, "y0": 610.0, "x1": 210.0, "y1": 625.0},
            "metadata": {
                "first_line": "1 Introduction",
                "line_count": 1,
                "char_count": 14,
                "max_font_size": 12.0,
                "layout_role": "single_column",
                "column_hint": "single",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "The introduction paragraph should be reclassified under the structural introduction heading.",
            "page_no": 1,
            "block_index": 6,
            "bbox": {"x0": 80.0, "y0": 632.0, "x1": 510.0, "y1": 690.0},
            "metadata": {
                "first_line": "The introduction paragraph should be reclassified under the structural introduction heading.",
                "line_count": 3,
                "char_count": 87,
                "max_font_size": 10.0,
                "layout_role": "single_column",
                "column_hint": "single",
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "Repeated Title",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 180.0, "y0": 44.0, "x1": 410.0, "y1": 58.0},
            "metadata": {
                "first_line": "Repeated Title",
                "line_count": 1,
                "char_count": 14,
                "max_font_size": 10.0,
                "layout_role": "single_column",
                "column_hint": "single",
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))

    figure_dir = tmp_path / "figures" / str(paper_id)
    table_dir = tmp_path / "tables" / str(paper_id)
    equation_dir = tmp_path / "equations" / str(paper_id)
    for path in (figure_dir, table_dir, equation_dir):
        path.mkdir(parents=True, exist_ok=True)

    (figure_dir / "page_001_img_001.png").write_bytes(b"\x89PNG\r\n\x1a\nimg")
    (figure_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_images": 1,
                "images": [
                    {
                        "id": 1,
                        "page_no": 1,
                        "file_name": "page_001_img_001.png",
                        "figure_type": "embedded",
                        "figure_caption": "Figure 1: Overview",
                        "figure_number": "1",
                        "figure_body": "Overview",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 90.0, "y0": 128.0, "x1": 500.0, "y1": 360.0},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (table_dir / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (equation_dir / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_front_matter_structural",
        blocks=blocks,
        metadata={"title": "Repeated Title"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.count("Repeated Title") == 1
    assert "Alice Example 1, Bob Example 2, Carol Example 1" in markdown
    assert "1 Example University 2 Example Lab" in markdown
    assert markdown.count("## Abstract") == 1
    assert markdown.count("## Introduction") == 1
    assert "\n1 Introduction\n" not in markdown
    assert markdown.index("## Abstract") < markdown.index("This abstract body should remain under the abstract heading")
    assert markdown.index("## Introduction") < markdown.index("The introduction paragraph should be reclassified under the structural introduction heading.")


def test_export_pdf_to_markdown_anchors_figure_to_caption_block_not_early_visual_label(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 120
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 220.0, "x1": 120.0, "y1": 236.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "Sequence/Monocular 3D Occupancy Segmentation",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 318.0, "y0": 223.0, "x1": 554.0, "y1": 250.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "This abstract body stays in the abstract.",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 58.0, "y0": 250.0, "x1": 290.0, "y1": 330.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "1. Introduction",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 58.0, "y0": 584.0, "x1": 170.0, "y1": 600.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
        {
            "text": "Figure 1. Overview figure.",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 317.0, "y0": 313.0, "x1": 555.0, "y1": 357.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
        {
            "text": "This introduction paragraph should precede the figure in markdown ordering.",
            "page_no": 1,
            "block_index": 5,
            "bbox": {"x0": 316.0, "y0": 376.0, "x1": 554.0, "y1": 450.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))

    figure_dir = tmp_path / "figures" / str(paper_id)
    table_dir = tmp_path / "tables" / str(paper_id)
    equation_dir = tmp_path / "equations" / str(paper_id)
    for path in (figure_dir, table_dir, equation_dir):
        path.mkdir(parents=True, exist_ok=True)

    (figure_dir / "page_001_img_001.png").write_bytes(b"\x89PNG\r\n\x1a\nimg")
    (figure_dir / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_images": 1,
                "images": [
                    {
                        "id": 1,
                        "page_no": 1,
                        "file_name": "page_001_img_001.png",
                        "figure_type": "embedded",
                        "figure_caption": "Figure 1. Overview figure.",
                        "figure_number": "1",
                        "figure_body": "Overview figure.",
                        "section_canonical": "introduction",
                        "section_title": "Introduction",
                        "bbox": {"x0": 324.7, "y0": 181.5, "x1": 612.0, "y1": 309.6},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (table_dir / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (equation_dir / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_caption_anchor",
        blocks=blocks,
        metadata={"title": "Caption Anchoring"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.index("## Abstract") < markdown.index("This abstract body stays in the abstract.")
    assert markdown.index("## Introduction") < markdown.index("![Figure 1](assets/figures/page_001_img_001.png)")
    assert markdown.index("![Figure 1](assets/figures/page_001_img_001.png)") > markdown.index("## Introduction")


def test_export_pdf_to_markdown_reflows_pdf_linebreaks_and_dehyphenates_prose(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 121
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 120.0, "x1": 120.0, "y1": 136.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": (
                "Relying on in-domain annotations and precise sensor-rig pri-\n"
                "ors, existing 3D occupancy prediction methods are limited\n"
                "in both scalability and out-of-domain generalization."
            ),
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 150.0, "x1": 320.0, "y1": 220.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
                "line_count": 3,
                "char_count": 146,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
        manifest_name = "manifest.json"
        empty_payload = {"paper_id": paper_id, "num_tables": 0, "tables": []} if kind == "tables" else (
            {"paper_id": paper_id, "num_images": 0, "images": []} if kind == "figures" else {"paper_id": paper_id, "num_equations": 0, "equations": []}
        )
        (path / manifest_name).write_text(json.dumps(empty_payload, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_reflow",
        blocks=blocks,
        metadata={"title": "Reflow Sample"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert "sensor-rig pri-\nors" not in markdown
    assert "sensor-rig priors, existing 3D occupancy prediction methods are limited in both scalability" in markdown
    assert "out-of-domain generalization." in markdown
