from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

import pymupdf

logger = logging.getLogger(__name__)


def _thumbnail_root() -> Path:
    configured = os.getenv("THUMBNAIL_OUTPUT_DIR", "").strip()
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        root = (Path.cwd() / ".ia_phase1_data" / "thumbnails").expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _paper_thumbnail_dir(paper_id: int) -> Path:
    path = _thumbnail_root() / str(int(paper_id))
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_paper_thumbnail_file(paper_id: int) -> Path:
    return _paper_thumbnail_dir(paper_id) / "thumbnail.png"


def generate_and_store_paper_thumbnail(pdf_path: str | Path, paper_id: int) -> Dict[str, Any]:
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_path = resolve_paper_thumbnail_file(paper_id)
    render_scale = max(0.25, float(os.getenv("THUMBNAIL_RENDER_SCALE", "1.2")))

    doc = pymupdf.open(str(pdf_path))
    try:
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(render_scale, render_scale), alpha=False)
        pix.save(str(output_path))
    finally:
        doc.close()

    return {
        "paper_id": int(paper_id),
        "thumbnail_path": str(output_path),
        "page_no": 1,
    }
