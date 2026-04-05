from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from ia_phase1 import parser


def test_sanitize_extracted_text_removes_invalid_unicode() -> None:
    cleaned = parser._sanitize_extracted_text("A\x00B\ud835C")
    assert cleaned == "AB\uFFFDC"


def test_describe_google_drive_source_detects_exportable_links() -> None:
    doc = parser.describe_google_drive_source(
        "https://docs.google.com/document/d/abc123/edit?usp=sharing"
    )
    sheet = parser.describe_google_drive_source(
        "https://docs.google.com/spreadsheets/d/sheet456/edit#gid=0"
    )
    slide = parser.describe_google_drive_source(
        "https://docs.google.com/presentation/d/slide789/edit"
    )
    drive = parser.describe_google_drive_source(
        "https://drive.google.com/file/d/file321/view?usp=sharing"
    )

    assert doc == {
        "source_kind": "google_doc_export",
        "file_id": "abc123",
        "download_url": "https://docs.google.com/document/d/abc123/export?format=pdf",
    }
    assert sheet == {
        "source_kind": "google_sheet_export",
        "file_id": "sheet456",
        "download_url": "https://docs.google.com/spreadsheets/d/sheet456/export?format=pdf",
    }
    assert slide == {
        "source_kind": "google_slide_export",
        "file_id": "slide789",
        "download_url": "https://docs.google.com/presentation/d/slide789/export/pdf",
    }
    assert drive == {
        "source_kind": "google_drive_file",
        "file_id": "file321",
        "download_url": "https://drive.google.com/uc?export=download&id=file321",
    }


def test_extract_pages_and_blocks(sample_pdf: Path) -> None:
    pages = parser.extract_pages(sample_pdf)
    assert len(pages) == 2
    assert pages[0][0] == 1
    assert "Abstract" in pages[0][1]
    assert "Method" in pages[1][1]

    blocks = parser.extract_text_blocks(sample_pdf)
    assert len(blocks) >= 3
    assert all("text" in block for block in blocks)
    assert all("metadata" in block for block in blocks)
    assert {block["page_no"] for block in blocks} == {1, 2}
    assert any(block["metadata"].get("lines") for block in blocks)
    first_with_lines = next(block for block in blocks if block["metadata"].get("lines"))
    first_line = first_with_lines["metadata"]["lines"][0]
    assert "text" in first_line
    assert "bbox" in first_line
    assert isinstance(first_line.get("spans"), list)


def test_extract_text_blocks_respects_page_allowlist(sample_pdf: Path) -> None:
    blocks = parser.extract_text_blocks(sample_pdf, page_allowlist=[2])

    assert blocks
    assert {block["page_no"] for block in blocks} == {2}
    assert any("Method" in str(block.get("text") or "") for block in blocks)
    assert all("Abstract" not in str(block.get("text") or "") for block in blocks)


def _build_two_column_order_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((144, 48, 452, 76), "A Two Column Paper", fontsize=18, align=1)
    page.insert_textbox((198, 82, 398, 102), "Author One / Author Two", fontsize=11, align=1)
    page.insert_textbox((12, 120, 34, 340), "arXiv:\n2603.99999v1\n[cs.CV]\n24 Mar 2026", fontsize=8)
    page.insert_textbox((72, 120, 270, 250), "Left column introduction paragraph with stable reading order. " * 3, fontsize=11)
    page.insert_textbox((72, 266, 270, 396), "Left column continuation paragraph that should remain before the right column. " * 3, fontsize=11)
    page.insert_textbox((320, 120, 520, 250), "Right column related work paragraph with separate content. " * 3, fontsize=11)
    page.insert_textbox((320, 266, 520, 396), "Right column method paragraph with distinct text. " * 3, fontsize=11)
    doc.save(str(path))
    doc.close()


def _build_first_page_preamble_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((120, 84, 475, 118), "MemDLM: Memory-Enhanced DLM Training", fontsize=18, align=1)
    page.insert_textbox((150, 150, 445, 182), "Zehua Pei 1, Hui-Ling Zhen 2, Bei Yu 1", fontsize=10, align=1)
    page.insert_textbox((165, 182, 430, 204), "1 Example University 2 Example Lab", fontsize=9, align=1)
    page.insert_textbox((285, 220, 330, 238), "Abstract", fontsize=12, align=1)
    page.insert_textbox(
        (145, 246, 470, 410),
        "This abstract paragraph should remain before chart labels on the first page. " * 8,
        fontsize=10,
        align=0,
    )
    page.insert_textbox((105, 458, 220, 476), "Standard MDLM", fontsize=5, align=0)
    page.insert_textbox((110, 652, 505, 708), "Figure 1: Needle-in-a-Haystack results overview.", fontsize=10, align=0)
    doc.save(str(path))
    doc.close()


def _build_single_column_equation_noise_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((54, 84, 260, 104), "3.2. On-Policy Trajectory Sampling", fontsize=11)
    page.insert_textbox(
        (54, 112, 540, 196),
        "A fundamental limitation of the SFT initialization is the distribution shift problem. "
        "The student policy accumulates errors and drifts into unfamiliar states where its behavior is undefined. " * 2,
        fontsize=10,
    )
    page.insert_textbox(
        (54, 200, 540, 286),
        "To address this, the method switches to dynamic on-policy sampling and collects trajectories "
        "from the student's own induced state distribution. This converts failure states into trainable examples. " * 2,
        fontsize=10,
    )
    page.insert_textbox((270, 318, 542, 346), "q_t(a) = pi_tea(a|s_t). (4)", fontsize=10)
    page.insert_textbox((54, 360, 240, 380), "3.3. Dense Teacher Supervision", fontsize=11)
    page.insert_textbox(
        (54, 388, 540, 470),
        "Instead of relying on sparse outcome rewards, a frozen teacher provides dense token-level supervision "
        "for every student-visited state. This immediately accelerates convergence and teaches recovery behavior. " * 2,
        fontsize=10,
    )
    page.insert_textbox((294, 790, 304, 804), "6", fontsize=9, align=1)
    doc.save(str(path))
    doc.close()


def _build_two_column_with_inflow_full_width_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((72, 104, 270, 220), "Left column upper paragraph should be read first and stay above the bridge block. " * 3, fontsize=10)
    page.insert_textbox((320, 104, 520, 220), "Right column upper paragraph should still follow the left upper paragraph. " * 3, fontsize=10)
    page.insert_textbox(
        (72, 236, 520, 340),
        "This full-width bridge paragraph belongs in the middle of the page body and should appear before the lower column segments. " * 2,
        fontsize=10,
    )
    page.insert_textbox((72, 372, 270, 500), "Left column lower paragraph should come after the full-width bridge. " * 3, fontsize=10)
    page.insert_textbox((320, 372, 520, 500), "Right column lower paragraph should come last within the body flow. " * 3, fontsize=10)
    doc.save(str(path))
    doc.close()


def test_extract_text_blocks_orders_two_column_pages_and_pushes_margin_notes_last(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "two_column.pdf"
    _build_two_column_order_pdf(pdf_path)

    blocks = parser.extract_text_blocks(pdf_path)
    texts = [" ".join(str(block.get("text") or "").split()) for block in blocks]

    assert texts[0].startswith("Author One / Author Two")
    assert texts[1].startswith("Left column introduction paragraph")
    assert texts[2].startswith("Left column continuation paragraph")
    assert texts[3].startswith("Right column related work paragraph")
    assert texts[4].startswith("Right column method paragraph")
    assert texts[-1].startswith("arXiv:")
    assert blocks[-1]["metadata"]["layout_role"] == "margin_note"


def test_extract_text_blocks_keeps_first_page_preamble_before_visual_labels(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "first_page_preamble.pdf"
    _build_first_page_preamble_pdf(pdf_path)

    blocks = parser.extract_text_blocks(pdf_path)
    texts = [" ".join(str(block.get("text") or "").split()) for block in blocks]

    title_pos = next(i for i, text in enumerate(texts) if text.startswith("MemDLM: Memory-Enhanced DLM Training"))
    author_pos = next(i for i, text in enumerate(texts) if text.startswith("Zehua Pei 1"))
    abstract_block_pos = next(i for i, text in enumerate(texts) if "This abstract paragraph should remain" in text)
    label_pos = next(i for i, text in enumerate(texts) if text.startswith("Standard MDLM"))

    assert title_pos < author_pos < abstract_block_pos < label_pos


def test_extract_text_blocks_does_not_false_positive_one_column_pages_from_headings_and_equations(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "single_column_equation_noise.pdf"
    _build_single_column_equation_noise_pdf(pdf_path)

    blocks = parser.extract_text_blocks(pdf_path)
    texts = [" ".join(str(block.get("text") or "").split()) for block in blocks]

    heading_32 = next(i for i, text in enumerate(texts) if text.startswith("3.2. On-Policy Trajectory Sampling"))
    para_32_a = next(i for i, text in enumerate(texts) if text.startswith("A fundamental limitation of the SFT initialization"))
    para_32_b = next(i for i, text in enumerate(texts) if text.startswith("To address this, the method switches to dynamic on-policy sampling"))
    heading_33 = next(i for i, text in enumerate(texts) if text.startswith("3.3. Dense Teacher Supervision"))
    para_33 = next(i for i, text in enumerate(texts) if text.startswith("Instead of relying on sparse outcome rewards"))

    assert heading_32 < para_32_a < para_32_b < heading_33 < para_33


def test_extract_text_blocks_keeps_mid_page_full_width_prose_in_flow_on_two_column_pages(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "two_column_inflow_full_width.pdf"
    _build_two_column_with_inflow_full_width_pdf(pdf_path)

    blocks = parser.extract_text_blocks(pdf_path)
    texts = [" ".join(str(block.get("text") or "").split()) for block in blocks]

    left_upper = next(i for i, text in enumerate(texts) if text.startswith("Left column upper paragraph"))
    right_upper = next(i for i, text in enumerate(texts) if text.startswith("Right column upper paragraph"))
    bridge = next(i for i, text in enumerate(texts) if text.startswith("This full-width bridge paragraph"))
    left_lower = next(i for i, text in enumerate(texts) if text.startswith("Left column lower paragraph"))
    right_lower = next(i for i, text in enumerate(texts) if text.startswith("Right column lower paragraph"))

    assert left_upper < right_upper < bridge < left_lower < right_lower


@pytest.mark.asyncio
async def test_resolve_any_to_pdf_direct_url(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_download(url: str, out_path: Path) -> None:
        out_path.write_bytes(sample_pdf.read_bytes())

    monkeypatch.setattr(parser, "_download_pdf", fake_download)
    monkeypatch.setattr(parser, "_guess_title_from_pdf", lambda _: "Sample Title")

    title, out_path = await parser.resolve_any_to_pdf(
        "https://example.test/paper.pdf",
        output_dir=tmp_path,
    )
    assert title == "Sample Title"
    assert out_path.exists()
    assert out_path.suffix == ".pdf"


@pytest.mark.asyncio
async def test_resolve_any_to_pdf_from_landing_page(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = """
    <html>
      <head>
        <meta name="citation_pdf_url" content="https://example.test/files/test.pdf" />
      </head>
      <body></body>
    </html>
    """

    async def fake_fetch_text(url: str) -> str:
        return html

    async def fake_download(url: str, out_path: Path) -> None:
        out_path.write_bytes(sample_pdf.read_bytes())

    monkeypatch.setattr(parser, "_fetch_text", fake_fetch_text)
    monkeypatch.setattr(parser, "_download_pdf", fake_download)
    monkeypatch.setattr(parser, "_guess_title_from_pdf", lambda _: "Landing Title")

    title, out_path = await parser.resolve_any_to_pdf(
        "https://landing-page.test/paper",
        output_dir=tmp_path,
    )
    assert title == "Landing Title"
    assert out_path.exists()


@pytest.mark.asyncio
async def test_resolve_any_to_pdf_google_doc_export(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    async def fake_download(url: str, out_path: Path) -> None:
        seen["url"] = url
        out_path.write_bytes(sample_pdf.read_bytes())

    monkeypatch.setattr(parser, "_download_pdf", fake_download)
    monkeypatch.setattr(parser, "_guess_title_from_pdf", lambda _: "Google Doc Title")

    title, out_path = await parser.resolve_any_to_pdf(
        "https://docs.google.com/document/d/abc123/edit?usp=sharing",
        output_dir=tmp_path,
    )

    assert seen["url"] == "https://docs.google.com/document/d/abc123/export?format=pdf"
    assert title == "Google Doc Title"
    assert out_path.exists()
