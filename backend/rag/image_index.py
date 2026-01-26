from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from pypdf import PdfReader

from .vision import caption_image

logger = logging.getLogger(__name__)


@dataclass
class FigureRecord:
    paper_id: int
    paper_title: str
    page_number: int
    image_path: str
    figure_number: Optional[int] = None
    caption: Optional[str] = None
    source_pdf: Optional[str] = None


class _ClipEmbedder:
    def __init__(self) -> None:
        try:
            import open_clip
            import torch
            from PIL import Image
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "open-clip-torch, torch, and pillow are required for image embeddings. "
                "Install them and restart the backend."
            ) from exc

        model_name = os.getenv("IMAGE_EMBEDDING_MODEL", "ViT-B-32")
        pretrained = os.getenv("IMAGE_EMBEDDING_PRETRAINED", "openai")

        self._torch = torch
        self._Image = Image
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self._tokenizer = open_clip.get_tokenizer(model_name)
        self._model.eval()
        self._device = os.getenv("IMAGE_EMBEDDING_DEVICE", "cpu")
        self._model.to(self._device)

    def embed_image(self, image_path: str) -> List[float]:
        image = self._Image.open(image_path).convert("RGB")
        image_input = self._preprocess(image).unsqueeze(0).to(self._device)
        with self._torch.no_grad():
            features = self._model.encode_image(image_input)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].cpu().tolist()

    def embed_text(self, text: str) -> List[float]:
        tokens = self._tokenizer([text]).to(self._device)
        with self._torch.no_grad():
            features = self._model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].cpu().tolist()


class ImageEmbeddings(Embeddings):
    def __init__(self) -> None:
        self._embedder = _ClipEmbedder()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embedder.embed_image(path) for path in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embedder.embed_text(text)


def _extract_figures_with_pymupdf(pdf_path: Path, output_dir: Path) -> List[Tuple[int, str]]:
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "PyMuPDF is required for figure extraction. Install pymupdf and restart."
        ) from exc

    doc = fitz.open(str(pdf_path))
    extracted: List[Tuple[int, str]] = []
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        images = page.get_images(full=True)
        for img_index, img in enumerate(images, start=1):
            xref = img[0]
            base = doc.extract_image(xref)
            image_bytes = base.get("image")
            ext = base.get("ext", "png")
            filename = f"page_{page_index + 1}_img_{img_index}.{ext}"
            output_dir.mkdir(parents=True, exist_ok=True)
            image_path = output_dir / filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            extracted.append((page_index + 1, str(image_path)))
    return extracted


def _extract_figures_with_pypdf(pdf_path: Path, output_dir: Path) -> List[Tuple[int, str]]:
    extracted: List[Tuple[int, str]] = []
    reader = PdfReader(str(pdf_path))
    for page_index, page in enumerate(reader.pages, start=1):
        try:
            images = page.images
        except Exception:
            images = []
        for img_index, image in enumerate(images, start=1):
            data = image.data if hasattr(image, "data") else None
            if not data:
                continue
            ext = getattr(image, "ext", "png")
            filename = f"page_{page_index}_img_{img_index}.{ext}"
            output_dir.mkdir(parents=True, exist_ok=True)
            image_path = output_dir / filename
            with open(image_path, "wb") as f:
                f.write(data)
            extracted.append((page_index, str(image_path)))
    return extracted


def _extract_page_texts(pdf_path: Path) -> Dict[int, str]:
    reader = PdfReader(str(pdf_path))
    texts: Dict[int, str] = {}
    for page_index, page in enumerate(reader.pages, start=1):
        texts[page_index] = page.extract_text() or ""
    return texts


def _extract_figures(
    pdf_path: Path,
    output_dir: Path,
    prefer_pymupdf: bool = True,
) -> List[Tuple[int, str]]:
    if prefer_pymupdf:
        try:
            return _extract_figures_with_pymupdf(pdf_path, output_dir)
        except Exception as exc:
            logger.warning("PyMuPDF extraction failed: %s", exc)
    return _extract_figures_with_pypdf(pdf_path, output_dir)


def _match_captions(page_text: str) -> List[Tuple[Optional[int], str]]:
    captions: List[Tuple[Optional[int], str]] = []
    for line in page_text.splitlines():
        match = re.search(r"(Figure|Fig\.)\s*(\d+)", line, re.IGNORECASE)
        if match:
            number = int(match.group(2))
            captions.append((number, line.strip()))
    return captions


def build_image_index(
    pdf_paths: Iterable[str],
    metadata_by_path: Dict[str, Dict[str, Any]],
    figure_dir: str,
    index_dir: str,
) -> int:
    pdf_paths = list(pdf_paths)
    if not pdf_paths:
        logger.info("No PDFs provided for image indexing.")
        return 0

    figure_root = Path(figure_dir)
    index_path = Path(index_dir)
    index_path.mkdir(parents=True, exist_ok=True)

    figure_records: List[FigureRecord] = []
    for raw_path in pdf_paths:
        pdf_path = Path(raw_path).expanduser().resolve()
        meta = metadata_by_path.get(str(pdf_path), {})
        paper_id_raw = meta.get("paper_id")
        if paper_id_raw is None:
            logger.warning("Skipping image indexing for %s because paper_id is missing.", pdf_path)
            continue
        paper_id = int(paper_id_raw)
        paper_title = meta.get("paper_title") or pdf_path.stem
        per_paper_dir = figure_root / str(paper_id)
        extracted = _extract_figures(pdf_path, per_paper_dir)
        if not extracted:
            continue
        page_texts = _extract_page_texts(pdf_path)
        caption_cache: Dict[int, List[Tuple[Optional[int], str]]] = {}
        for page_number, image_path in extracted:
            if page_number not in caption_cache:
                caption_cache[page_number] = _match_captions(page_texts.get(page_number, ""))
            captions = caption_cache[page_number]
            figure_number = None
            caption = None
            if captions:
                figure_number, caption = captions.pop(0)
            if not caption and os.getenv("VISION_CAPTION_ENABLED", "false").lower() in {"1", "true", "yes"}:
                caption = caption_image(image_path)
            figure_records.append(
                FigureRecord(
                    paper_id=paper_id,
                    paper_title=paper_title,
                    page_number=page_number,
                    image_path=image_path,
                    figure_number=figure_number,
                    caption=caption,
                    source_pdf=str(pdf_path),
                )
            )

    if not figure_records:
        logger.info("No figures extracted for image index.")
        return 0

    documents: List[Document] = []
    for record in figure_records:
        documents.append(
            Document(
                page_content=record.image_path,
                metadata={
                    "paper_id": record.paper_id,
                    "paper_title": record.paper_title,
                    "page_number": record.page_number,
                    "figure_number": record.figure_number,
                    "caption": record.caption,
                    "image_path": record.image_path,
                    "source": record.image_path,
                    "source_pdf": record.source_pdf,
                    "kind": "figure",
                },
            )
        )

    embeddings = ImageEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(str(index_path))
    logger.info("Saved image index to %s with %s figures", index_dir, len(documents))
    return len(documents)


def load_image_index(index_dir: str) -> FAISS:
    embeddings = ImageEmbeddings()
    return FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)


def query_image_index(
    question: str,
    index_dir: str,
    k: int = 4,
    paper_ids: Optional[Iterable[int]] = None,
) -> List[Dict[str, Any]]:
    index_path = Path(index_dir)
    if not index_path.exists():
        return []
    try:
        vectorstore = load_image_index(str(index_path))
        docs = vectorstore.similarity_search(question, k=k)
    except Exception as exc:
        logger.warning("Image index query failed: %s", exc)
        return []
    if paper_ids:
        allowed = {int(pid) for pid in paper_ids}
        docs = [
            doc
            for doc in docs
            if int(doc.metadata.get("paper_id", -1)) in allowed
        ]
    results: List[Dict[str, Any]] = []
    index = 1
    for doc in docs:
        meta = doc.metadata or {}
        caption = meta.get("caption") or "No caption available."
        figure_number = meta.get("figure_number")
        label = f"Figure {figure_number}" if figure_number else "Figure"
        results.append(
            {
                "text": f"{label}: {caption}",
                "meta": meta,
                "index": index,
                "chunk_count": 1,
            }
        )
        index += 1
    return results
