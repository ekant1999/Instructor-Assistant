from __future__ import annotations

from pathlib import Path

import pytest

from ia_phase1 import parser


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
