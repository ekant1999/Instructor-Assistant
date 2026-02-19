from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pymupdf
from bs4 import BeautifulSoup
from pypdf import PdfReader

USER_AGENT = "ia-phase1-parser/0.1 (+https://example.local)"


def _default_pdf_dir() -> Path:
    configured = (Path.cwd() / ".ia_phase1_data" / "pdfs")
    configured.mkdir(parents=True, exist_ok=True)
    return configured


def _safe_filename(seed: str) -> str:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{h}.pdf"


async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def _download_pdf(url: str, out_path: Path) -> None:
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=60,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        out_path.write_bytes(response.content)


def _guess_title_from_pdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        metadata = reader.metadata or {}
        title = (metadata.title or "").strip()
        if title:
            return title
        first = reader.pages[0].extract_text() or ""
        first = first.strip().split("\n", 1)[0][:160]
        return first or pdf_path.name
    except Exception:
        return pdf_path.name


async def resolve_any_to_pdf(input_str: str, output_dir: Optional[Path] = None) -> Tuple[str, Path]:
    """
    Resolve DOI, landing page URL, arXiv URL, or direct PDF URL into a local PDF.

    Returns:
        (title, local_pdf_path)
    """
    pdf_dir = (output_dir or _default_pdf_dir()).expanduser().resolve()
    pdf_dir.mkdir(parents=True, exist_ok=True)

    value = input_str.strip()
    if not value:
        raise ValueError("input_str cannot be empty")

    # DOI shortcut
    if re.match(r"^10\.\d{4,9}/", value):
        landing_url = f"https://doi.org/{value}"
        html = await _fetch_text(landing_url)
    else:
        if value.lower().endswith(".pdf"):
            pdf_url = value
            out = pdf_dir / _safe_filename(pdf_url)
            await _download_pdf(pdf_url, out)
            return _guess_title_from_pdf(out), out
        html = await _fetch_text(value)

    soup = BeautifulSoup(html, "html.parser")
    pdf_url: Optional[str] = None
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content", "").strip():
        pdf_url = meta["content"].strip()

    if not pdf_url:
        link = soup.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        if link:
            href = str(link.get("href") or "").strip()
            if href.startswith("//"):
                href = "https:" + href
            pdf_url = href

    if not pdf_url:
        raise RuntimeError("Could not locate a PDF link on the source page.")

    out = pdf_dir / _safe_filename(pdf_url)
    await _download_pdf(pdf_url, out)
    return _guess_title_from_pdf(out), out


def extract_pages(pdf_path: Path) -> List[Tuple[int, str]]:
    """
    Simple page-level text extraction using pypdf.
    """
    pages: List[Tuple[int, str]] = []
    reader = PdfReader(str(pdf_path))
    for idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").replace("\x00", "")
        pages.append((idx + 1, text))
    return pages


def extract_text_blocks(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Block-level extraction using PyMuPDF with geometry + text style metadata.
    """
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = pymupdf.open(str(pdf_path))
    blocks: List[Dict[str, Any]] = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_dict = page.get_text("dict")
            text_blocks = [b for b in page_dict.get("blocks", []) if b.get("type") == 0]

            block_idx = 0
            for block in text_blocks:
                lines = block.get("lines", [])
                text_lines: List[str] = []
                span_sizes: List[float] = []
                span_fonts: List[str] = []
                bold_spans = 0
                total_spans = 0

                for line in lines:
                    spans = line.get("spans", [])
                    line_parts: List[str] = []
                    for span in spans:
                        span_text = str(span.get("text") or "").replace("\x00", "")
                        if not span_text.strip():
                            continue
                        line_parts.append(span_text)
                        size = span.get("size")
                        try:
                            span_sizes.append(float(size))
                        except (TypeError, ValueError):
                            pass
                        font_name = str(span.get("font") or "")
                        if font_name:
                            span_fonts.append(font_name)
                        total_spans += 1
                        if "bold" in font_name.lower():
                            bold_spans += 1
                    if line_parts:
                        text_lines.append("".join(line_parts).strip())

                text = "\n".join(text_lines).strip().replace("\x00", "")
                if not text:
                    continue

                bbox = block.get("bbox", [0, 0, 0, 0])
                first_line = text_lines[0].strip() if text_lines else text.splitlines()[0].strip()
                max_font = max(span_sizes) if span_sizes else 0.0
                avg_font = (sum(span_sizes) / len(span_sizes)) if span_sizes else 0.0
                min_font = min(span_sizes) if span_sizes else 0.0
                bold_ratio = (bold_spans / total_spans) if total_spans else 0.0

                blocks.append(
                    {
                        "page_no": page_num + 1,
                        "block_index": block_idx,
                        "text": text,
                        "bbox": {
                            "x0": float(bbox[0]) if len(bbox) > 0 else 0.0,
                            "y0": float(bbox[1]) if len(bbox) > 1 else 0.0,
                            "x1": float(bbox[2]) if len(bbox) > 2 else 0.0,
                            "y1": float(bbox[3]) if len(bbox) > 3 else 0.0,
                        },
                        "metadata": {
                            "first_line": first_line,
                            "line_count": len(text_lines),
                            "char_count": len(text),
                            "max_font_size": round(max_font, 3),
                            "avg_font_size": round(avg_font, 3),
                            "min_font_size": round(min_font, 3),
                            "bold_ratio": round(bold_ratio, 3),
                            "font_names": sorted(set(span_fonts))[:6],
                        },
                    }
                )
                block_idx += 1
    finally:
        doc.close()

    return blocks
