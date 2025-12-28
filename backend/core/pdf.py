from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import List, Tuple

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

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
    pages: List[Tuple[int, str]] = []
    reader = PdfReader(str(pdf_path))
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        pages.append((i + 1, txt))
    return pages
