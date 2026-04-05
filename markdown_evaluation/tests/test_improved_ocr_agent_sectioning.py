from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ocr_agent.hybrid_pdf_extractor as base_hybrid
from improved_ocr_agent.hybrid_pdf_extractor import DummyOCRBackend, HybridPDFExtractor
from improved_ocr_agent.non_ocr_routing import DocumentContentProfile, NonOcrRun, PageContentProfile


def _build_sample_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Page one body")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Page two body")
    doc.save(str(path))
    doc.close()
    return path


def test_improved_hybrid_extractor_merges_non_ocr_and_ocr_pages_in_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = _build_sample_pdf(tmp_path / "mixed.pdf")
    page_modes = iter(["simple_text", "ocr"])

    monkeypatch.setattr(HybridPDFExtractor, "_classify_document", lambda self, stats: "hybrid_paper")
    monkeypatch.setattr(HybridPDFExtractor, "_classify_page", lambda self, stat, doc_mode: next(page_modes))
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_build_non_ocr_document_profile",
        lambda self, page_numbers, page_stats, total_pages: DocumentContentProfile(
            document_handler="ia_phase1",
            page_profiles=[PageContentProfile(page_num=1, ia_score=4, native_score=0, handler="ia_phase1")],
            runs=[NonOcrRun(handler="ia_phase1", page_numbers=[1])],
            scores={"ia_score": 4, "native_score": 0},
        ),
    )
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_extract_non_ocr_segments",
        lambda self, pages: SimpleNamespace(
            page_segments={1: "## Introduction\n\nNon-OCR body.\n"},
            document_title="mixed",
        ),
    )
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_extract_ocr_page",
        lambda self, page_fitz, page_num, page_hint=None: "\n\n<!-- OCR page 2 -->\n\nOCR body.\n\n",
    )

    markdown = HybridPDFExtractor(str(pdf_path), ocr_backend=DummyOCRBackend()).extract_to_markdown()

    assert markdown.startswith("# mixed")
    assert "<!-- page 1 mode: simple_text -->" in markdown
    assert "<!-- page 2 mode: ocr -->" in markdown
    assert markdown.index("Non-OCR body.") < markdown.index("OCR body.")
    assert "## Introduction" in markdown
    assert "<!-- OCR page 2 -->" in markdown


def test_improved_hybrid_extractor_keeps_ocr_pages_identical_to_base_extractor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = _build_sample_pdf(tmp_path / "ocr_only.pdf")

    monkeypatch.setattr(base_hybrid.HybridPDFExtractor, "_classify_document", lambda self, stats: "ocr")
    monkeypatch.setattr(base_hybrid.HybridPDFExtractor, "_classify_page", lambda self, stat, doc_mode: "ocr")
    monkeypatch.setattr(HybridPDFExtractor, "_classify_document", lambda self, stats: "ocr")
    monkeypatch.setattr(HybridPDFExtractor, "_classify_page", lambda self, stat, doc_mode: "ocr")

    base_markdown = base_hybrid.HybridPDFExtractor(str(pdf_path), ocr_backend=DummyOCRBackend()).extract_to_markdown()
    improved_markdown = HybridPDFExtractor(str(pdf_path), ocr_backend=DummyOCRBackend()).extract_to_markdown()

    assert improved_markdown == base_markdown


def test_improved_hybrid_extractor_uses_native_non_ocr_runs_for_textheavy_pages(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = _build_sample_pdf(tmp_path / "native.pdf")
    page_modes = iter(["simple_text", "ocr"])

    monkeypatch.setattr(HybridPDFExtractor, "_classify_document", lambda self, stats: "hybrid_paper")
    monkeypatch.setattr(HybridPDFExtractor, "_classify_page", lambda self, stat, doc_mode: next(page_modes))
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_build_non_ocr_document_profile",
        lambda self, page_numbers, page_stats, total_pages: DocumentContentProfile(
            document_handler="native",
            page_profiles=[PageContentProfile(page_num=1, ia_score=0, native_score=5, handler="native")],
            runs=[NonOcrRun(handler="native", page_numbers=[1])],
            scores={"ia_score": 0, "native_score": 5},
        ),
    )
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_extract_native_non_ocr_runs",
        lambda self, runs, page_modes, doc_fitz, doc_plumber, base_size: {1: "## Section 1\n\nNative body.\n"},
    )
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_extract_non_ocr_segments",
        lambda self, pages: (_ for _ in ()).throw(AssertionError("ia_phase1 bridge should not run")),
    )
    monkeypatch.setattr(
        HybridPDFExtractor,
        "_extract_ocr_page",
        lambda self, page_fitz, page_num, page_hint=None: "\n\n<!-- OCR page 2 -->\n\nOCR body.\n\n",
    )

    markdown = HybridPDFExtractor(str(pdf_path), ocr_backend=DummyOCRBackend()).extract_to_markdown()

    assert markdown.startswith("# native")
    assert "## Section 1" in markdown
    assert "Native body." in markdown
    assert "<!-- OCR page 2 -->" in markdown
