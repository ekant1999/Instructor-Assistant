from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import pytest
import pymupdf


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    """
    Build a deterministic 2-page PDF fixture for parser/section/figure tests.
    """
    path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Abstract")
    page1.insert_text((72, 96), "This is the abstract block for testing.")
    page1.insert_text((72, 140), "1 Introduction")
    page1.insert_text((72, 164), "Introduction starts on page one.")

    page2 = doc.new_page()
    page2.insert_text((72, 72), "2 Method")
    page2.insert_text((72, 96), "Method section appears on page two.")
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def sectioned_blocks() -> List[Dict[str, object]]:
    return [
        {
            "text": "Abstract text block",
            "page_no": 1,
            "block_index": 0,
            "bbox": {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 40.0},
            "metadata": {
                "section_canonical": "abstract",
                "section_title": "Abstract",
                "section_source": "heuristic",
                "section_confidence": 0.8,
            },
        },
        {
            "text": "Introduction text block",
            "page_no": 1,
            "block_index": 1,
            "bbox": {"x0": 0.0, "y0": 50.0, "x1": 100.0, "y1": 90.0},
            "metadata": {
                "section_canonical": "introduction",
                "section_title": "Introduction",
                "section_source": "heuristic",
                "section_confidence": 0.85,
            },
        },
        {
            "text": "Method text block",
            "page_no": 2,
            "block_index": 0,
            "bbox": {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 40.0},
            "metadata": {
                "section_canonical": "methodology",
                "section_title": "Method",
                "section_source": "heuristic",
                "section_confidence": 0.9,
            },
        },
    ]
