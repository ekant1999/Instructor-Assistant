from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
import pymupdf  # PyMuPDF for block-level extraction

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "research-notes-py/1.0 (+https://example.local)"


def _safe_filename(seed: str) -> str:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{h}.pdf"


async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


async def _download_pdf(url: str, out_path: Path):
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        out_path.write_bytes(r.content)


def _guess_title_from_pdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        md = reader.metadata or {}
        title = (md.title or "").strip()
        if title:
            return title
        first = reader.pages[0].extract_text() or ""
        return first.strip().split("\n", 1)[0][:120] or pdf_path.name
    except Exception:
        return pdf_path.name


async def resolve_any_to_pdf(input_str: str) -> Tuple[str, Path]:
    """
    Accepts DOI (e.g. 10.xxxx/....) or a landing page URL or a direct PDF URL.
    Returns (title, pdf_path).
    """
    # DOI -> doi.org
    if re.match(r"^10\.\d{4,9}/", input_str):
        landing = f"https://doi.org/{input_str}"
        html = await _fetch_text(landing)
    else:
        if input_str.lower().endswith(".pdf"):
            pdf_url = input_str
            out = PDF_DIR / _safe_filename(pdf_url)
            await _download_pdf(pdf_url, out)
            return _guess_title_from_pdf(out), out
        html = await _fetch_text(input_str)

    soup = BeautifulSoup(html, "html.parser")
    pdf_url = None
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content", "").strip():
        pdf_url = meta["content"].strip()
    if not pdf_url:
        link = soup.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
        if link:
            pdf_url = link["href"]
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url

    if not pdf_url:
        raise RuntimeError("Could not locate a PDF on the landing page.")

    out = PDF_DIR / _safe_filename(pdf_url)
    await _download_pdf(pdf_url, out)
    return _guess_title_from_pdf(out), out


def extract_pages(pdf_path: Path) -> List[Tuple[int, str]]:
    """
    Legacy function for page-level extraction (kept for backward compatibility).
    For new code, use extract_text_blocks() instead.
    """
    pages: List[Tuple[int, str]] = []
    reader = PdfReader(str(pdf_path))
    for i, page in enumerate(reader.pages):
        txt = (page.extract_text() or "").replace("\x00", "")
        pages.append((i + 1, txt))
    return pages


def extract_text_blocks(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text blocks with page, block index, and bounding boxes using PyMuPDF.
    
    Returns list of blocks, each containing:
    - page_no: Page number (1-indexed)
    - block_index: Block position on page (0-indexed)
    - text: Block text content
    - bbox: Bounding box dictionary with x0, y0, x1, y1
    
    This provides more granular location tracking than page-level extraction.
    """
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
                        "page_no": page_num + 1,  # 1-indexed
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
