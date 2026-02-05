from __future__ import annotations

import re
from typing import List, Tuple

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "research-notes-py/1.0 (+https://example.local)"
GOOGLE_DOC_RE = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")

MAX_WEB_CHARS = 500_000
MAX_WEB_CHUNKS = 500


def _google_doc_id(url: str) -> str | None:
    match = GOOGLE_DOC_RE.search(url)
    return match.group(1) if match else None


async def _fetch(url: str) -> httpx.Response:
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r


def _clean_text(text: str) -> str:
    return " ".join(text.replace("\x00", "").split()).strip()


def _extract_text_from_html(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form", "svg", "canvas"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)

    container = soup.find("article") or soup.find("main") or soup.body or soup
    parts: List[str] = []
    for tag in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre"]):
        text = tag.get_text(" ", strip=True)
        text = _clean_text(text)
        if text:
            parts.append(text)

    text = "\n\n".join(parts)
    return title, text


def _simple_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    clean = " ".join(text.split())
    if not clean:
        return []
    if len(clean) <= chunk_size:
        return [clean]
    chunks: List[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        if end < len(clean):
            for delim in [". ", "? ", "! "]:
                pos = clean.rfind(delim, start, end)
                if pos != -1 and pos > start + 100:
                    end = pos + 1
                    break
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(0, end - overlap) if overlap > 0 else end
    return chunks


def chunk_web_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=overlap
        )
        chunks = [c.strip() for c in splitter.split_text(text) if c.strip()]
    except Exception:
        chunks = _simple_chunks(text, chunk_size, overlap)
    return chunks[:MAX_WEB_CHUNKS]


async def extract_web_document(url: str) -> Tuple[str, str]:
    doc_id = _google_doc_id(url)
    if doc_id:
        txt_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        text = (await _fetch(txt_url)).text
        title = f"Google Doc {doc_id}"
        try:
            html_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
            html = (await _fetch(html_url)).text
            html_title, _ = _extract_text_from_html(html)
            if html_title:
                title = html_title
        except Exception:
            pass
        text = text[:MAX_WEB_CHARS]
        return title, text

    resp = await _fetch(url)
    content_type = resp.headers.get("content-type", "").lower()
    body = resp.text
    if "text/html" in content_type or "<html" in body.lower():
        title, text = _extract_text_from_html(body)
    else:
        title = url
        text = body
    title = title or url
    text = text[:MAX_WEB_CHARS]
    return title, text

