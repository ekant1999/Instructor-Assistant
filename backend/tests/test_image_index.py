from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from backend.rag import image_index


def test_build_image_index_for_papers_materializes_object_backed_pdf(tmp_path: Path, monkeypatch) -> None:
    resolved_pdf = tmp_path / "paper.pdf"
    resolved_pdf.write_bytes(b"%PDF-1.4 fake")
    calls: list[tuple[int, object]] = []

    @contextmanager
    def fake_materialize_primary_pdf_path(paper_id: int, raw_pdf_path=None):
        calls.append((paper_id, raw_pdf_path))
        yield resolved_pdf

    monkeypatch.setattr(image_index, "materialize_primary_pdf_path", fake_materialize_primary_pdf_path)
    monkeypatch.setattr(
        image_index,
        "_extract_figures",
        lambda pdf_path, output_dir: [(2, str(output_dir / "page_2_img_1.png"))],
    )
    monkeypatch.setattr(
        image_index,
        "_extract_page_texts",
        lambda pdf_path: {2: "Figure 1. CLIP image-text alignment example"},
    )
    monkeypatch.setattr(image_index, "ImageEmbeddings", lambda: object())

    class _FakeVectorStore:
        saved_path: str | None = None

        def save_local(self, path: str) -> None:
            self.saved_path = path

    class _FakeFAISS:
        docs = None

        @classmethod
        def from_documents(cls, docs, embeddings):
            cls.docs = docs
            return _FakeVectorStore()

    monkeypatch.setattr(image_index, "FAISS", _FakeFAISS)

    count = image_index.build_image_index_for_papers(
        [{"id": 91, "title": "Stored Paper", "pdf_path": None}],
        str(tmp_path / "figures"),
        str(tmp_path / "index"),
    )

    assert count == 1
    assert calls == [(91, None)]
    assert _FakeFAISS.docs is not None
    assert _FakeFAISS.docs[0].metadata["paper_id"] == 91
    assert _FakeFAISS.docs[0].metadata["caption"] == "Figure 1. CLIP image-text alignment example"

