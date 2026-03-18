from __future__ import annotations

from pathlib import Path

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
