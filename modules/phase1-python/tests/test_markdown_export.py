from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import ia_phase1.markdown_export.export as markdown_export_module
from ia_phase1.markdown_export import MarkdownExportConfig, export_pdf_to_markdown
from ia_phase1.markdown_export.quality import MarkdownRenderAudit, audit_rendered_markdown


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
    assert manifest["sectioning"]["strategy"] == "preannotated"
    assert manifest["assets"]["tables"][0]["markdown_json_path"] == "assets/tables/table_0001.json"
    assert manifest["assets"]["equations"][0]["latex"] == "x = y + z"
    assert result.sectioning_strategy == "preannotated"


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


def test_export_pdf_to_markdown_keeps_distinct_section_titles_with_same_canonical(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 121
    blocks = [
        {
            "text": "3 Problem Formulation",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 20.0, "x1": 180.0, "y1": 35.0},
            "metadata": {
                "first_line": "3 Problem Formulation",
                "section_canonical": "methodology",
                "section_title": "Problem Formulation",
                "section_level": 2,
                "section_index": 3,
            },
        },
        {
            "text": "Problem formulation paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 40.0, "x1": 220.0, "y1": 70.0},
            "metadata": {
                "first_line": "Problem formulation paragraph.",
                "section_canonical": "methodology",
                "section_title": "Problem Formulation",
                "section_level": 2,
                "section_index": 3,
            },
        },
        {
            "text": "4 Methods",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 10.0, "y0": 90.0, "x1": 120.0, "y1": 105.0},
            "metadata": {
                "first_line": "4 Methods",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Methods paragraph.",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 10.0, "y0": 110.0, "x1": 220.0, "y1": 140.0},
            "metadata": {
                "first_line": "Methods paragraph.",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
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
        output_dir=tmp_path / "markdown_same_canonical_sections",
        blocks=blocks,
        metadata={"title": "Same Canonical Sections"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.count("## Problem Formulation") == 1
    assert markdown.count("## Methods") == 1
    assert markdown.index("Problem formulation paragraph.") < markdown.index("## Methods")
    assert markdown.index("## Methods") < markdown.index("Methods paragraph.")


def test_export_pdf_to_markdown_skips_algorithmic_scaffold_lines(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 122
    blocks = [
        {
            "text": "4 Methods",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 10.0, "y0": 20.0, "x1": 120.0, "y1": 35.0},
            "metadata": {
                "first_line": "4 Methods",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Methods paragraph explaining the pipeline.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 10.0, "y0": 40.0, "x1": 240.0, "y1": 70.0},
            "metadata": {
                "first_line": "Methods paragraph explaining the pipeline.",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "Algorithm 1 Training Loop",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 10.0, "y0": 90.0, "x1": 220.0, "y1": 105.0},
            "metadata": {
                "first_line": "Algorithm 1 Training Loop",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "1: K wb ← ∅",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 10.0, "y0": 110.0, "x1": 160.0, "y1": 122.0},
            "metadata": {
                "first_line": "1: K wb ← ∅",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "for each d j ∈ D i do",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 10.0, "y0": 126.0, "x1": 180.0, "y1": 138.0},
            "metadata": {
                "first_line": "for each d j ∈ D i do",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
            },
        },
        {
            "text": "end for",
            "page_no": 1,
            "block_index": 5,
            "bbox": {"x0": 10.0, "y0": 142.0, "x1": 90.0, "y1": 154.0},
            "metadata": {
                "first_line": "end for",
                "section_canonical": "methodology",
                "section_title": "Methods",
                "section_level": 2,
                "section_index": 4,
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
        output_dir=tmp_path / "markdown_algorithm_scaffold",
        blocks=blocks,
        metadata={"title": "Algorithm Filter"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.count("## Methods") == 1
    assert "Methods paragraph explaining the pipeline." in markdown
    assert "Algorithm 1 Training Loop" not in markdown
    assert "1: K wb ← ∅" not in markdown
    assert "for each d j ∈ D i do" not in markdown
    assert "\nend for\n" not in markdown


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
    assert "Sequence/Monocular 3D Occupancy Segmentation" not in markdown
    assert "\nFigure 1. Overview figure.\n" not in markdown


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


def test_export_pdf_to_markdown_rejects_placeholder_and_equationish_headings(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 122
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 80.0, "x1": 120.0, "y1": 96.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Clean abstract paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 110.0, "x1": 260.0, "y1": 150.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "{reference}",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 90.0, "x1": 140.0, "y1": 108.0},
            "metadata": {
                "section_canonical": "appendix",
                "section_title": "{reference}",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "x_i = g_\\theta(q_i, d_i)",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 118.0, "x1": 220.0, "y1": 134.0},
            "metadata": {
                "section_canonical": "other",
                "section_title": "Document Body",
                "section_level": 2,
                "max_font_size": 11.0,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
        empty_payload = {"paper_id": paper_id, "num_tables": 0, "tables": []} if kind == "tables" else (
            {"paper_id": paper_id, "num_images": 0, "images": []} if kind == "figures" else {"paper_id": paper_id, "num_equations": 0, "equations": []}
        )
        (path / "manifest.json").write_text(json.dumps(empty_payload, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_bad_heading_filter",
        blocks=blocks,
        metadata={"title": "Bad Heading Filter"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert "## {reference}" not in markdown
    assert "\n## x_i = g_\\theta(q_i, d_i)\n" not in markdown
    assert "\n{reference}\n" not in markdown


def test_export_pdf_to_markdown_uses_conservative_fallback_for_heading_explosions(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 123
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 120.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Clean abstract paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 130.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "First appendix paragraph.",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 90.0, "x1": 240.0, "y1": 120.0},
            "metadata": {
                "section_canonical": "appendix_alpha",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
        {
            "text": "Second appendix paragraph.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 130.0, "x1": 240.0, "y1": 160.0},
            "metadata": {
                "section_canonical": "appendix_beta",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
        {
            "text": "Third appendix paragraph.",
            "page_no": 2,
            "block_index": 2,
            "bbox": {"x0": 40.0, "y0": 170.0, "x1": 240.0, "y1": 200.0},
            "metadata": {
                "section_canonical": "appendix_gamma",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
        {
            "text": "Fourth appendix paragraph.",
            "page_no": 2,
            "block_index": 3,
            "bbox": {"x0": 40.0, "y0": 210.0, "x1": 240.0, "y1": 240.0},
            "metadata": {
                "section_canonical": "appendix_delta",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)
    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(
                conservative_recommended=True,
                issue_count=1,
                issues=["force conservative"],
            )
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "equation_0001.png").write_bytes(b"\x89PNG\r\n\x1a\neq")
    (tmp_path / "equations" / str(paper_id) / "equation_0001.json").write_text(json.dumps({"id": 1}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(
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
                        "text": "x = y + z",
                        "latex": "x = y + z",
                        "latex_source": "text_fallback",
                        "render_mode": "latex",
                        "section_canonical": "abstract",
                        "section_title": "Abstract",
                        "bbox": {"x0": 40.0, "y0": 150.0, "x1": 140.0, "y1": 164.0},
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
        output_dir=tmp_path / "markdown_conservative_fallback",
        blocks=blocks,
        metadata={"title": "Conservative Fallback"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert result.audit is not None
    assert result.audit.conservative_recommended is False
    assert markdown.count("## Hyperparameters") == 0
    assert "$$\nx = y + z\n$$" not in markdown
    assert "> Equation 1 JSON: `assets/equations/equation_0001.json`" not in markdown
    assert audit_rendered_markdown(markdown, metadata={"title": "Conservative Fallback", "page_count": 2}).issue_count == 0


def test_export_pdf_to_markdown_keeps_numeric_subsections_in_conservative_mode(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 124
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 120.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Clean abstract paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 130.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "4 Methods",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 150.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "appendix_alpha",
                "section_title": "Hyperparameters",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Methods paragraph.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 240.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "appendix_beta",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
        {
            "text": "4.2\nUtility Gate",
            "page_no": 2,
            "block_index": 2,
            "bbox": {"x0": 40.0, "y0": 136.0, "x1": 160.0, "y1": 154.0},
            "metadata": {
                "section_canonical": "appendix_gamma",
                "section_title": "Hyperparameters",
                "section_level": 2,
                "line_count": 2,
                "char_count": 16,
                "max_font_size": 10.9,
            },
        },
        {
            "text": "Utility paragraph.",
            "page_no": 2,
            "block_index": 3,
            "bbox": {"x0": 40.0, "y0": 160.0, "x1": 240.0, "y1": 190.0},
            "metadata": {
                "section_canonical": "appendix_delta",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)
    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(
                conservative_recommended=True,
                issue_count=1,
                issues=["force conservative"],
            )
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_conservative_subsections",
        blocks=blocks,
        metadata={"title": "Conservative Subsections"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert audit_calls["count"] == 2
    assert "## Hyperparameters" not in markdown
    assert "### Utility Gate" in markdown
    assert "\n4.2\nUtility Gate\n" not in markdown


def test_export_pdf_to_markdown_keeps_known_top_level_headings_in_conservative_mode(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 126
    blocks = [
        {
            "text": "Introduction",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 150.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Intro paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
        {
            "text": "2. Related works",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 170.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "related_work",
                "section_title": "Related works",
                "section_level": 1,
                "max_font_size": 11.9,
            },
        },
        {
            "text": "Related work paragraph.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 240.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "other",
                "section_title": "Document Body",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)
    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(
                conservative_recommended=True,
                issue_count=1,
                issues=["force conservative"],
            )
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_conservative_related_work",
        blocks=blocks,
        metadata={"title": "Conservative Related Works"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert "## Related works" in markdown
    assert "Related work paragraph." in markdown


def test_export_pdf_to_markdown_keeps_preliminaries_heading_in_conservative_mode(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 128
    blocks = [
        {
            "text": "1 Introduction",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 160.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Intro paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
        {
            "text": "2 Preliminaries",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 180.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "preliminaries",
                "section_title": "Preliminaries",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Preliminaries paragraph.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 240.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "preliminaries",
                "section_title": "Preliminaries",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)
    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(
                conservative_recommended=True,
                issue_count=1,
                issues=["force conservative"],
            )
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_conservative_preliminaries",
        blocks=blocks,
        metadata={"title": "Conservative Preliminaries"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert "## Preliminaries" in markdown
    assert "Preliminaries paragraph." in markdown


def test_export_pdf_to_markdown_suppresses_prompt_internal_references_heading_in_conservative_mode(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 127
    blocks = [
        {
            "text": "G\nPrompt Templates",
            "page_no": 10,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 170.0, "y1": 96.0},
            "metadata": {
                "section_canonical": "prompt_templates",
                "section_title": "Prompt Templates",
                "section_level": 2,
                "line_count": 2,
                "char_count": 18,
                "max_font_size": 11.9,
            },
        },
        {
            "text": "Extractive evidence.",
            "page_no": 10,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 110.0, "x1": 200.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "prompt_templates",
                "section_title": "Prompt Templates",
                "section_level": 2,
            },
        },
        {
            "text": "References",
            "page_no": 10,
            "block_index": 2,
            "bbox": {"x0": 40.0, "y0": 136.0, "x1": 140.0, "y1": 152.0},
            "metadata": {
                "section_canonical": "references",
                "section_title": "References",
                "section_level": 2,
                "max_font_size": 11.9,
            },
        },
        {
            "text": "[Doc 1] Example evidence block.",
            "page_no": 10,
            "block_index": 3,
            "bbox": {"x0": 40.0, "y0": 162.0, "x1": 260.0, "y1": 188.0},
            "metadata": {
                "section_canonical": "references",
                "section_title": "References",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)
    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(
                conservative_recommended=True,
                issue_count=1,
                issues=["force conservative"],
            )
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_conservative_prompt_refs",
        blocks=blocks,
        metadata={"title": "Conservative Prompt References"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert "## Prompt Templates" in markdown
    assert "## References" not in markdown


def test_infer_document_title_skips_margin_note_arxiv_header() -> None:
    blocks = [
        {
            "text": "Actual Paper Title for Testing",
            "page_no": 1,
            "bbox": {"x0": 60.0, "y0": 48.0, "x1": 320.0, "y1": 72.0},
            "metadata": {"max_font_size": 15.0, "line_count": 1},
        },
        {
            "text": "arXiv:2603.22241v1 [cs.CL] 23 Mar 2026",
            "page_no": 1,
            "layout_role": "margin_note",
            "bbox": {"x0": 20.0, "y0": 22.0, "x1": 250.0, "y1": 42.0},
            "metadata": {"max_font_size": 20.0, "line_count": 1, "layout_role": "margin_note"},
        },
    ]

    inferred = markdown_export_module._infer_document_title_from_blocks(blocks)

    assert inferred == "Actual Paper Title for Testing"


def test_title_like_front_matter_blocks_are_not_misclassified_as_author_lines() -> None:
    assert markdown_export_module._looks_like_front_matter_name_block(
        "MemDLM: Memory-Enhanced DLM Training"
    ) is False
    assert markdown_export_module._looks_like_front_matter_author_block(
        "End-to-End Training for Unified Tokenization and Latent Denoising"
    ) is False


def test_equation_record_is_not_renderable_in_references() -> None:
    assert (
        markdown_export_module._equation_record_is_renderable(
            {
                "equation_number": "2024",
                "section_canonical": "references",
                "section_title": "References",
                "text": "2024",
            }
        )
        is False
    )


def test_parse_structural_heading_block_accepts_multiline_appendix_heading() -> None:
    parsed = markdown_export_module._parse_structural_heading_block(
        "B\nW RITE B ACK-RAG Prevents Answer\nLeakage",
        block={
            "metadata": {
                "line_count": 3,
                "char_count": 42,
                "max_font_size": 11.955,
            }
        },
    )

    assert parsed is not None
    assert parsed["canonical"] == "appendix"
    assert parsed["title"] == "W RITE B ACK-RAG Prevents Answer Leakage"
    assert parsed["level"] == 2


def test_parse_structural_heading_block_rejects_numeric_axis_titles() -> None:
    parsed = markdown_export_module._parse_structural_heading_block(
        "0.5",
        block={"metadata": {"line_count": 1, "char_count": 3, "max_font_size": 10.5}},
    )

    assert parsed is None
    assert (
        markdown_export_module._should_emit_section_heading(
            section_canonical="results",
            section_title="15",
            section_level=2,
            conservative_mode=False,
        )
        is False
    )


def test_parse_structural_heading_block_accepts_numbered_subheadings() -> None:
    parsed_method = markdown_export_module._parse_structural_heading_block(
        "3.1. 3D Reconstruction with Segmentation Forcing",
        block={"metadata": {"line_count": 1, "char_count": 44, "max_font_size": 11.0, "section_canonical": "methodology"}},
    )
    parsed_results = markdown_export_module._parse_structural_heading_block(
        "4.1. Main results",
        block={"metadata": {"line_count": 1, "char_count": 17, "max_font_size": 11.0, "section_canonical": "experiments"}},
    )

    assert parsed_method is not None
    assert parsed_method["level"] == 3
    assert parsed_method["title"] == "3D Reconstruction with Segmentation Forcing"
    assert parsed_method["canonical"] == "methodology"

    assert parsed_results is not None
    assert parsed_results["level"] == 3
    assert parsed_results["title"] == "Main results"
    assert parsed_results["canonical"] == "results"


def test_conservative_top_level_heading_candidate_requires_title_canonical_alignment() -> None:
    assert (
        markdown_export_module._is_conservative_top_level_heading_candidate(
            {
                "title": "Distiller",
                "canonical": "related_work",
                "level": 2,
                "number": "",
                "confidence": 0.95,
            }
        )
        is False
    )


def test_export_pdf_to_markdown_keeps_split_numbered_subheadings_in_conservative_mode(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 129
    blocks = [
        {
            "text": "4 Method",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 140.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Method paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 126.0},
            "metadata": {
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_level": 2,
            },
        },
        {
            "text": "4.1",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 40.0, "y0": 136.0, "x1": 70.0, "y1": 152.0},
            "metadata": {
                "section_canonical": "single_frame_3d_reconstruction_with_learned_priors",
                "section_title": "Single-Frame 3D Reconstruction with Learned Priors",
                "section_level": 3,
                "line_count": 1,
                "char_count": 3,
                "max_font_size": 10.9,
            },
        },
        {
            "text": "Single-Frame 3D Reconstruction with Learned Priors",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 82.0, "y0": 136.0, "x1": 330.0, "y1": 152.0},
            "metadata": {
                "section_canonical": "single_frame_3d_reconstruction_with_learned_priors",
                "section_title": "Single-Frame 3D Reconstruction with Learned Priors",
                "section_level": 3,
                "line_count": 1,
                "char_count": 51,
                "max_font_size": 10.9,
            },
        },
        {
            "text": "Subheading paragraph.",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 40.0, "y0": 160.0, "x1": 260.0, "y1": 190.0},
            "metadata": {
                "section_canonical": "single_frame_3d_reconstruction_with_learned_priors",
                "section_title": "Single-Frame 3D Reconstruction with Learned Priors",
                "section_level": 3,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)
    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(
                conservative_recommended=True,
                issue_count=1,
                issues=["force conservative"],
            )
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_conservative_split_subheading",
        blocks=blocks,
        metadata={"title": "Conservative Split Subheading"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert "### Single-Frame 3D Reconstruction with Learned Priors" in markdown
    assert "\n4.1\n" not in markdown
    assert "Subheading paragraph." in markdown


def test_algorithmic_scaffold_detection_catches_input_output_lines() -> None:
    assert (
        markdown_export_module._looks_like_algorithmic_scaffold_text(
            "Input: Student Policy πθ Output: Optimized Policy πθ*"
        )
        is True
    )


def test_rendered_table_owned_noise_block_detects_caption_and_rows() -> None:
    render_state = {
        "tables_by_page": {
            2: [
                {
                    "bbox": {"x0": 80.0, "y0": 220.0, "x1": 420.0, "y1": 320.0},
                    "caption": "Table 2: Main Results on LIBERO.",
                }
            ]
        }
    }
    caption_block = {
        "page_no": 2,
        "bbox": {"x0": 90.0, "y0": 184.0, "x1": 410.0, "y1": 210.0},
    }
    row_block = {
        "page_no": 2,
        "bbox": {"x0": 100.0, "y0": 248.0, "x1": 395.0, "y1": 278.0},
    }

    assert (
        markdown_export_module._is_rendered_table_owned_noise_block(
            caption_block,
            text="Table 2: Main Results on LIBERO.",
            render_state=render_state,
        )
        is True
    )
    assert (
        markdown_export_module._is_rendered_table_owned_noise_block(
            row_block,
            text="Method Success Rate Steps",
            render_state=render_state,
        )
        is True
    )


def test_equation_record_is_not_renderable_for_prompt_template_fragments() -> None:
    assert (
        markdown_export_module._equation_record_is_renderable(
            {
                "section_canonical": "appendix",
                "section_title": "Prompt Templates",
                "text": "[Doc <index>] <sentence>",
            }
        )
        is False
    )
    assert (
        markdown_export_module._equation_record_is_renderable(
            {
                "section_canonical": "appendix",
                "section_title": "Rationale for using Naive RAG for Analysis",
                "text": "Utility scores: s rag = 1.0, s nr = 0.0, ∆ = 1.0",
            }
        )
        is False
    )
    assert (
        markdown_export_module._equation_record_is_renderable(
            {
                "section_canonical": "methodology",
                "section_title": "Methodology",
                "text": "q XSD6qiBKJLoGb2iN0tbL9a79TFvzVnZzCH6A+vzB/S9kG4=</latexit> (x t|x 0)",
            }
        )
        is False
    )
    assert (
        markdown_export_module._equation_record_is_renderable(
            {
                "section_canonical": "appendix",
                "section_title": "Representative Write-Back Examples",
                "text": "Utility scores: s rag = 1.0, s nr = 0.0, ∆ = 1.0",
            }
        )
        is False
    )


def test_equation_record_is_not_conservatively_renderable_for_low_quality_fallbacks() -> None:
    assert (
        markdown_export_module._equation_record_is_conservatively_renderable(
            {
                "equation_number": "",
                "latex_source": "text_fallback",
                "latex_confidence": 0.46,
                "text": "L MDLM(θ) = E t∼U(0,1),x 0",
            }
        )
        is False
    )
    assert (
        markdown_export_module._equation_record_is_conservatively_renderable(
            {
                "equation_number": "3",
                "latex_source": "text_fallback",
                "latex_confidence": 0.46,
                "latex": "L static = E x 0,x t∼q(·|x 0) [− log p \\\\theta(x 0|x t)] .\\n\\\\tag{3}",
                "text": "L static = E x 0,x t∼q(·|x 0) [− log p θ(x 0|x t)] .",
            }
        )
        is True
    )


def test_equation_residue_text_is_skipped() -> None:
    assert markdown_export_module._looks_like_equation_residue_text('"') is True
    assert markdown_export_module._looks_like_equation_residue_text("\\#") is True
    assert markdown_export_module._looks_like_equation_residue_text("|s|") is True
    assert markdown_export_module._looks_like_equation_residue_text("Clean narrative text.") is False


def test_export_pdf_to_markdown_keeps_appendix_letter_headings_in_conservative_mode(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 125
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 120.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Clean abstract paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 130.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "A Datasets",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 80.0, "x1": 160.0, "y1": 96.0},
            "metadata": {
                "section_canonical": "appendix_alpha",
                "section_title": "Hyperparameters",
                "section_level": 2,
                "line_count": 1,
                "char_count": 10,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Appendix dataset paragraph.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 104.0, "x1": 260.0, "y1": 140.0},
            "metadata": {
                "section_canonical": "appendix_beta",
                "section_title": "Hyperparameters",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setattr(markdown_export_module, "_ensure_section_metadata", lambda blocks, pdf_path, source_url: None)

    audit_calls = {"count": 0}

    def fake_audit(markdown: str, *, metadata: dict, blocks=None):
        audit_calls["count"] += 1
        if audit_calls["count"] == 1:
            return MarkdownRenderAudit(conservative_recommended=True, issue_count=1, issues=["force conservative"])
        return MarkdownRenderAudit()

    monkeypatch.setattr(markdown_export_module, "audit_rendered_markdown", fake_audit)

    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_equations": 0, "equations": []}, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_conservative_appendix",
        blocks=blocks,
        metadata={"title": "Conservative Appendix"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert result.render_mode == "conservative"
    assert "## Datasets" in markdown
    assert "\nA Datasets\n" not in markdown


def test_normalize_markdown_document_model_splits_late_reference_runs() -> None:
    model = markdown_export_module.MarkdownDocumentModel(
        sections=[
            markdown_export_module.MarkdownSectionNode(
                canonical="conclusion",
                title="Conclusion",
                level=2,
                page_start=8,
                page_end=10,
                elements=[
                    markdown_export_module.MarkdownParagraphNode(text="Closing discussion paragraph.", page_no=8),
                    markdown_export_module.MarkdownParagraphNode(
                        text="Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, and Hannaneh Hajishirzi. 2023. Self-rag: Learning to retrieve, generate, and critique through self-reflection. In The Twelfth International Conference on Learning Representations.",
                        page_no=9,
                    ),
                    markdown_export_module.MarkdownParagraphNode(
                        text="Sebastian Borgeaud, Arthur Mensch, Jordan Hoffmann, Trevor Cai, Eliza Rutherford, Katie Millican, George Bm Van Den Driessche, Jean-Baptiste Lespiau, Bogdan Damoc, Aidan Clark, and 1 others. 2022. Improving language models by retrieving from trillions of tokens. In International conference on machine learning, pages 2206–2240. PMLR.",
                        page_no=9,
                    ),
                    markdown_export_module.MarkdownParagraphNode(
                        text="Christopher Clark, Kenton Lee, Ming-Wei Chang, Tom Kwiatkowski, Michael Collins, and Kristina Toutanova. 2019. Boolq: Exploring the surprising difficulty of natural yes/no questions. In Proceedings of the 2019 conference of the North American chapter of the association for computational linguistics.",
                        page_no=10,
                    ),
                ],
            )
        ]
    )

    markdown_export_module._normalize_markdown_document_model(model)

    assert len(model.sections) == 2
    assert model.sections[0].canonical == "conclusion"
    assert model.sections[1].canonical == "references"
    assert model.sections[1].title == "References"


def test_normalize_markdown_document_model_splits_reference_runs_for_early_start_late_end_sections() -> None:
    model = markdown_export_module.MarkdownDocumentModel(
        sections=[
            markdown_export_module.MarkdownSectionNode(
                canonical="conclusion",
                title="Conclusion",
                level=2,
                page_start=4,
                page_end=12,
                elements=[
                    markdown_export_module.MarkdownParagraphNode(text="Closing discussion paragraph.", page_no=4),
                    markdown_export_module.MarkdownParagraphNode(text="Intermediate narrative text.", page_no=7),
                    markdown_export_module.MarkdownParagraphNode(
                        text="[1] Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, and Hannaneh Hajishirzi. 2023. Self-rag: Learning to retrieve, generate, and critique through self-reflection. In The Twelfth International Conference on Learning Representations.",
                        page_no=11,
                    ),
                    markdown_export_module.MarkdownParagraphNode(
                        text="[2] Sebastian Borgeaud, Arthur Mensch, Jordan Hoffmann, Trevor Cai, Eliza Rutherford, Katie Millican, George Bm Van Den Driessche, Jean-Baptiste Lespiau, Bogdan Damoc, Aidan Clark, and 1 others. 2022. Improving language models by retrieving from trillions of tokens. In International conference on machine learning, pages 2206–2240. PMLR.",
                        page_no=11,
                    ),
                    markdown_export_module.MarkdownParagraphNode(
                        text="[3] Christopher Clark, Kenton Lee, Ming-Wei Chang, Tom Kwiatkowski, Michael Collins, and Kristina Toutanova. 2019. Boolq: Exploring the surprising difficulty of natural yes/no questions. In Proceedings of the 2019 conference of the North American chapter of the association for computational linguistics.",
                        page_no=12,
                    ),
                ],
            )
        ]
    )

    markdown_export_module._normalize_markdown_document_model(model)

    assert len(model.sections) == 2
    assert model.sections[0].title == "Conclusion"
    assert model.sections[1].title == "References"


def test_normalize_markdown_document_model_absorbs_running_header_asset_sections() -> None:
    model = markdown_export_module.MarkdownDocumentModel(
        sections=[
            markdown_export_module.MarkdownSectionNode(
                canonical="introduction",
                title="Introduction",
                level=2,
                page_start=1,
                page_end=1,
                elements=[
                    markdown_export_module.MarkdownParagraphNode(text="Opening introduction paragraph with enough prose to count as narrative text.", page_no=1),
                    markdown_export_module.MarkdownAssetNode(kind="figure", record={"page_no": 1}, page_no=1),
                ],
            ),
            markdown_export_module.MarkdownSectionNode(
                canonical="introduction",
                title="Khan et al",
                level=2,
                page_start=2,
                page_end=2,
                elements=[
                    markdown_export_module.MarkdownAssetNode(kind="figure", record={"page_no": 2}, page_no=2),
                ],
            ),
            markdown_export_module.MarkdownSectionNode(
                canonical="introduction",
                title="Introduction",
                level=2,
                page_start=2,
                page_end=2,
                elements=[
                    markdown_export_module.MarkdownParagraphNode(text="Second introduction paragraph.", page_no=2),
                ],
            ),
            markdown_export_module.MarkdownSectionNode(
                canonical="appendix",
                title="KB Training",
                level=2,
                page_start=3,
                page_end=3,
                elements=[],
            ),
        ]
    )

    markdown_export_module._normalize_markdown_document_model(model)

    assert [section.title for section in model.sections] == ["Introduction"]
    assert len(model.sections[0].elements) == 4


def test_build_markdown_document_model_does_not_promote_figure_label_blocks_to_headings() -> None:
    blocks = [
        {
            "text": "4 Experiments",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 20.0, "y0": 20.0, "x1": 160.0, "y1": 34.0},
            "metadata": {
                "section_canonical": "experiments",
                "section_title": "Experiments",
                "section_level": 2,
                "max_font_size": 13.0,
            },
        },
        {
            "text": "Score",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 55.0, "y0": 95.0, "x1": 95.0, "y1": 106.0},
            "metadata": {
                "section_canonical": "experiments",
                "section_title": "Experiments",
                "section_level": 1,
                "max_font_size": 11.0,
            },
        },
        {
            "text": "Narrative text after the chart explains the observed result in ordinary prose.",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 20.0, "y0": 150.0, "x1": 220.0, "y1": 175.0},
            "metadata": {
                "section_canonical": "experiments",
                "section_title": "Experiments",
                "section_level": 1,
            },
        },
    ]
    bundled_assets = {
        "figures": [
            {
                "id": 1,
                "page_no": 1,
                "file_name": "page_001_vec_001.png",
                "figure_caption": "Figure 1: Chart caption",
                "figure_number": "1",
                "figure_type": "vector",
                "section_canonical": "experiments",
                "section_title": "Experiments",
                "bbox": {"x0": 20.0, "y0": 70.0, "x1": 200.0, "y1": 140.0},
            }
        ],
        "tables": [],
        "equations": [],
    }
    metadata = {"title": "Sample Paper", "paper_id": 1, "num_figures": 1, "num_tables": 0, "num_equations": 0}

    model = markdown_export_module._build_markdown_document_model(
        blocks=deepcopy(blocks),
        bundled_assets=bundled_assets,
        metadata=metadata,
        config=MarkdownExportConfig(ensure_assets=False),
        conservative_mode=True,
    )

    assert [section.title for section in model.sections] == ["Experiments"]
    assert not any(
        isinstance(element, markdown_export_module.MarkdownSubheadingNode) and element.title == "Score"
        for element in model.sections[0].elements
    )


def test_build_markdown_document_model_switches_top_level_section_before_later_subheading() -> None:
    blocks = [
        {
            "text": "5 Experiments",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 20.0, "y0": 20.0, "x1": 180.0, "y1": 34.0},
            "metadata": {
                "section_canonical": "experiments",
                "section_title": "Experiments",
                "section_level": 2,
                "max_font_size": 13.0,
            },
        },
        {
            "text": "Experimental setup paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 20.0, "y0": 40.0, "x1": 220.0, "y1": 60.0},
            "metadata": {
                "section_canonical": "experiments",
                "section_title": "Experiments",
                "section_level": 1,
            },
        },
        {
            "text": "6 Results",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 20.0, "y0": 90.0, "x1": 160.0, "y1": 104.0},
            "metadata": {
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "max_font_size": 13.0,
            },
        },
        {
            "text": "6.1 RQ1: Overall Performance",
            "page_no": 1,
            "block_index": 3,
            "bbox": {"x0": 24.0, "y0": 110.0, "x1": 220.0, "y1": 122.0},
            "metadata": {
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Results paragraph.",
            "page_no": 1,
            "block_index": 4,
            "bbox": {"x0": 20.0, "y0": 126.0, "x1": 220.0, "y1": 150.0},
            "metadata": {
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 1,
            },
        },
    ]
    model = markdown_export_module._build_markdown_document_model(
        blocks=deepcopy(blocks),
        bundled_assets={"figures": [], "tables": [], "equations": []},
        metadata={"title": "Sample Paper", "paper_id": 1},
        config=MarkdownExportConfig(ensure_assets=False),
        conservative_mode=True,
    )

    assert [section.title for section in model.sections] == ["Experiments", "Results"]
    assert any(
        isinstance(element, markdown_export_module.MarkdownSubheadingNode) and element.title == "RQ1: Overall Performance"
        for element in model.sections[1].elements
    )


def test_export_pdf_to_markdown_keeps_explicit_appendix_heading_authoritative_for_same_page_text(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 126
    blocks = [
        {
            "text": "Abstract",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 120.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Clean abstract paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 220.0, "y1": 130.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_level": 2,
            },
        },
        {
            "text": "H Representative Write-Back Examples",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 84.0, "x1": 260.0, "y1": 100.0},
            "metadata": {
                "section_canonical": "references",
                "section_title": "References",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "This qualitative appendix paragraph should remain under the appendix heading even when stale section metadata says references.",
            "page_no": 2,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 110.0, "x1": 300.0, "y1": 170.0},
            "metadata": {
                "section_canonical": "references",
                "section_title": "References",
                "section_level": 2,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
        empty_payload = {"paper_id": paper_id, "num_tables": 0, "tables": []} if kind == "tables" else (
            {"paper_id": paper_id, "num_images": 0, "images": []} if kind == "figures" else {"paper_id": paper_id, "num_equations": 0, "equations": []}
        )
        (path / "manifest.json").write_text(json.dumps(empty_payload, ensure_ascii=False), encoding="utf-8")

    result = export_pdf_to_markdown(
        sample_pdf,
        paper_id=paper_id,
        output_dir=tmp_path / "markdown_appendix_heading_authority",
        blocks=blocks,
        metadata={"title": "Appendix Heading Authority"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert "## Representative Write-Back Examples" in markdown
    assert markdown.count("## References") == 0
    assert markdown.index("## Representative Write-Back Examples") < markdown.index("This qualitative appendix paragraph should remain under the appendix heading")


def test_export_pdf_to_markdown_does_not_promote_asset_subheading_to_duplicate_top_level_section(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paper_id = 127
    blocks = [
        {
            "text": "6 Results",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 40.0, "y0": 70.0, "x1": 150.0, "y1": 86.0},
            "metadata": {
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "max_font_size": 12.0,
            },
        },
        {
            "text": "Results introduction paragraph.",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 40.0, "y0": 96.0, "x1": 260.0, "y1": 124.0},
            "metadata": {
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
            },
        },
        {
            "text": "6.1 RQ1: Overall Performance",
            "page_no": 1,
            "block_index": 2,
            "bbox": {"x0": 40.0, "y0": 136.0, "x1": 230.0, "y1": 152.0},
            "metadata": {
                "section_canonical": "results",
                "section_title": "Results",
                "section_level": 2,
                "max_font_size": 11.0,
            },
        },
    ]

    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    for kind in ("tables", "figures", "equations"):
        path = tmp_path / kind / str(paper_id)
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "tables" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_tables": 0, "tables": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "figures" / str(paper_id) / "manifest.json").write_text(json.dumps({"paper_id": paper_id, "num_images": 0, "images": []}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "equation_0001.png").write_bytes(b"\x89PNG\r\n\x1a\neq")
    (tmp_path / "equations" / str(paper_id) / "equation_0001.json").write_text(json.dumps({"id": 1}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "equations" / str(paper_id) / "manifest.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "num_equations": 1,
                "equations": [
                    {
                        "id": 1,
                        "equation_number": "1",
                        "page_no": 1,
                        "file_name": "equation_0001.png",
                        "json_file": "equation_0001.json",
                        "latex": "x = y + z",
                        "latex_source": "text_fallback",
                        "render_mode": "latex",
                        "section_canonical": "results",
                        "section_title": "RQ1: Overall Performance",
                        "bbox": {"x0": 40.0, "y0": 165.0, "x1": 160.0, "y1": 182.0},
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
        output_dir=tmp_path / "markdown_asset_subheading_context",
        blocks=blocks,
        metadata={"title": "Asset Subheading Context"},
        config=MarkdownExportConfig(ensure_assets=False),
    )

    markdown = result.markdown
    assert markdown.count("## Results") == 1
    assert markdown.count("### RQ1: Overall Performance") == 1


def test_asset_heading_section_prefers_nearest_structural_heading() -> None:
    page_entries = [
        (
            0,
            {
                "text": "D Datasets",
                "page_no": 12,
                "bbox": {"x0": 40.0, "y0": 260.0, "x1": 170.0, "y1": 276.0},
                "metadata": {"section_canonical": "datasets", "section_title": "Datasets", "section_level": 2},
            },
        ),
        (
            1,
            {
                "text": "E Hyperparameters",
                "page_no": 12,
                "bbox": {"x0": 40.0, "y0": 420.0, "x1": 220.0, "y1": 436.0},
                "metadata": {"section_canonical": "appendix", "section_title": "Hyperparameters", "section_level": 2},
            },
        ),
    ]

    above_record = {"bbox": {"x0": 70.0, "y0": 90.0, "x1": 520.0, "y1": 210.0}}
    below_record = {"bbox": {"x0": 310.0, "y0": 450.0, "x1": 490.0, "y1": 580.0}}

    assert markdown_export_module._asset_heading_section(above_record, page_entries) == ("appendix", "Datasets", 2)
    assert markdown_export_module._asset_heading_section(below_record, page_entries) == ("appendix", "Hyperparameters", 2)


def test_ensure_section_metadata_reannotates_inconsistent_preannotated_blocks(monkeypatch) -> None:
    blocks = [
        {
            "text": "2.1. Problem Formulation",
            "page_no": 3,
            "block_index": 0,
            "bbox": {"x0": 54.0, "y0": 100.0, "x1": 220.0, "y1": 120.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
        {
            "text": "We formalize the alignment problem as a sequential decision process with task-level supervision and delayed rewards. " * 2,
            "page_no": 3,
            "block_index": 1,
            "bbox": {"x0": 54.0, "y0": 128.0, "x1": 540.0, "y1": 190.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_level": 2,
            },
        },
        {
            "text": "3. Methodology",
            "page_no": 4,
            "block_index": 2,
            "bbox": {"x0": 54.0, "y0": 200.0, "x1": 180.0, "y1": 220.0},
            "metadata": {
                "section_canonical": "related_work",
                "section_title": "Related Work",
                "section_level": 2,
            },
        },
    ]

    def fake_annotate_blocks_with_sections(*, blocks, pdf_path, source_url):
        blocks[0]["metadata"].update({"section_canonical": "methodology", "section_title": "Problem Formulation", "section_level": 3})
        blocks[1]["metadata"].update({"section_canonical": "methodology", "section_title": "Problem Formulation", "section_level": 3})
        blocks[2]["metadata"].update({"section_canonical": "methodology", "section_title": "Methodology", "section_level": 2})
        return {
            "strategy": "heuristic",
            "candidate_headings": 2,
            "matched_headings": 2,
            "sections": [{"title": "Problem Formulation"}, {"title": "Methodology"}],
        }

    monkeypatch.setattr(markdown_export_module, "annotate_blocks_with_sections", fake_annotate_blocks_with_sections)
    report = markdown_export_module._ensure_section_metadata(
        blocks,
        pdf_path=Path("/tmp/fake.pdf"),
        source_url=None,
    )

    assert report["strategy"] == "heuristic"
    assert report["fallback_from"] == "preannotated"
    assert "validation_issues" in report
    assert blocks[0]["metadata"]["section_title"] == "Problem Formulation"
    assert blocks[2]["metadata"]["section_title"] == "Methodology"


def test_audit_rendered_markdown_flags_consecutive_subheadings_when_blocks_show_intervening_prose() -> None:
    markdown = "\n".join(
        [
            "## Methodology",
            "",
            "### Dataset",
            "",
            "### Hyperparameters",
            "",
            "### Analysis",
            "",
            "Deferred prose appears too late.",
            "",
        ]
    )
    blocks = [
        {
            "text": "A. Dataset",
            "page_no": 12,
            "bbox": {"x0": 54.0, "y0": 100.0, "x1": 180.0, "y1": 118.0},
        },
        {
            "text": "This prose block should have appeared between the appendix headings instead of after the entire run. " * 2,
            "page_no": 12,
            "bbox": {"x0": 54.0, "y0": 124.0, "x1": 540.0, "y1": 188.0},
        },
        {
            "text": "B. Hyperparameters",
            "page_no": 12,
            "bbox": {"x0": 54.0, "y0": 210.0, "x1": 220.0, "y1": 228.0},
        },
        {
            "text": "Another prose block is geometrically between Hyperparameters and Analysis on the page. " * 2,
            "page_no": 12,
            "bbox": {"x0": 54.0, "y0": 236.0, "x1": 540.0, "y1": 290.0},
        },
        {
            "text": "C. Analysis",
            "page_no": 12,
            "bbox": {"x0": 54.0, "y0": 318.0, "x1": 180.0, "y1": 336.0},
        },
    ]

    audit = audit_rendered_markdown(markdown, metadata={"page_count": 12}, blocks=blocks)

    assert audit.conservative_recommended is True
    assert any("consecutive heading runs missing prose" in issue for issue in audit.issues)


def test_asset_sort_order_uses_geometry_when_caption_block_order_is_late() -> None:
    record = {
        "page_no": 12,
        "caption": "Table 5: Detailed dataset statistics.",
        "bbox": {"x0": 70.0, "y0": 80.0, "x1": 520.0, "y1": 210.0},
    }
    page_entries = [
        (
            10,
            {
                "text": "Dataset Task Description",
                "page_no": 12,
                "bbox": {"x0": 72.0, "y0": 84.0, "x1": 520.0, "y1": 104.0},
            },
        ),
        (
            11,
            {
                "text": "NQ Open-domain QA ...",
                "page_no": 12,
                "bbox": {"x0": 72.0, "y0": 106.0, "x1": 520.0, "y1": 126.0},
            },
        ),
        (
            20,
            {
                "text": "D Datasets",
                "page_no": 12,
                "bbox": {"x0": 40.0, "y0": 260.0, "x1": 170.0, "y1": 276.0},
            },
        ),
        (
            30,
            {
                "text": "Table 5: Detailed dataset statistics.",
                "page_no": 12,
                "bbox": {"x0": 80.0, "y0": 220.0, "x1": 520.0, "y1": 236.0},
            },
        ),
    ]

    sort_order = markdown_export_module._asset_sort_order(
        "table",
        record,
        page_block_entries={12: page_entries},
        default_order=100,
    )

    assert sort_order < 20.0


def test_asset_sort_order_keeps_top_table_before_lower_same_page_table() -> None:
    page_entries = [
        (258, {"text": "BoolQ ...", "page_no": 12, "bbox": {"x0": 75.0, "y0": 110.0, "x1": 422.0, "y1": 129.0}}),
        (259, {"text": "zsRE ...", "page_no": 12, "bbox": {"x0": 75.0, "y0": 150.0, "x1": 423.0, "y1": 169.0}}),
        (260, {"text": "SQuAD ...", "page_no": 12, "bbox": {"x0": 75.0, "y0": 190.0, "x1": 422.0, "y1": 208.0}}),
        (271, {"text": "Hyperparameter Value", "page_no": 12, "bbox": {"x0": 312.0, "y0": 336.0, "x1": 468.0, "y1": 345.0}}),
        (272, {"text": "Retrieval Retriever ...", "page_no": 12, "bbox": {"x0": 312.0, "y0": 351.0, "x1": 487.0, "y1": 400.0}}),
        (273, {"text": "Gating ...", "page_no": 12, "bbox": {"x0": 312.0, "y0": 407.0, "x1": 462.0, "y1": 456.0}}),
        (274, {"text": "Distillation ...", "page_no": 12, "bbox": {"x0": 312.0, "y0": 462.0, "x1": 512.0, "y1": 541.0}}),
        (275, {"text": "Indexing ...", "page_no": 12, "bbox": {"x0": 312.0, "y0": 547.0, "x1": 525.0, "y1": 576.0}}),
        (276, {"text": "Table 6: Full hyperparameter settings used in the main experiments.", "page_no": 12, "bbox": {"x0": 305.0, "y0": 590.0, "x1": 524.0, "y1": 612.0}}),
        (278, {"text": "FEVER ...", "page_no": 12, "bbox": {"x0": 75.0, "y0": 130.0, "x1": 511.0, "y1": 149.0}}),
        (279, {"text": "HotpotQA ...", "page_no": 12, "bbox": {"x0": 75.0, "y0": 170.0, "x1": 513.0, "y1": 189.0}}),
        (280, {"text": "Table 5: Detailed dataset statistics used in our experiments.", "page_no": 12, "bbox": {"x0": 70.0, "y0": 223.0, "x1": 525.0, "y1": 245.0}}),
    ]
    top_record = {
        "page_no": 12,
        "caption": "Table 5: Detailed dataset statistics used in our experiments.",
        "bbox": {"x0": 72.0, "y0": 74.0, "x1": 522.0, "y1": 210.0},
    }
    lower_record = {
        "page_no": 12,
        "caption": "Table 6: Full hyperparameter settings used in the main experiments.",
        "bbox": {"x0": 316.0, "y0": 336.0, "x1": 487.0, "y1": 576.0},
    }

    top_sort = markdown_export_module._asset_sort_order(
        "table",
        top_record,
        page_block_entries={12: page_entries},
        default_order=100,
    )
    lower_sort = markdown_export_module._asset_sort_order(
        "table",
        lower_record,
        page_block_entries={12: page_entries},
        default_order=100,
    )

    assert top_sort < lower_sort
