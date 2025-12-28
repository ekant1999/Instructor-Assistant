"""PDF text extraction tools."""
from __future__ import annotations

from typing import Dict, List

from pypdf import PdfReader

from .utils import safe_path


def pdf_summary(pdf_path: str) -> Dict[str, object]:
    """Extract text from a PDF and return a capped preview."""
    path = safe_path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    text_parts: List[str] = []
    with open(path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts)
    text = text[:5000] if len(text) > 5000 else text
    return {
        "pdf_path": str(path),
        "extracted_text": text,
        "text_length": len(text),
        "note": "Text capped to 5000 characters for downstream models.",
    }

