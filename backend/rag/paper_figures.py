from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pymupdf

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIGURE_DIR = BACKEND_ROOT / "data" / "figures"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bbox_from_rect(rect: Any) -> Optional[Dict[str, float]]:
    if rect is None:
        return None
    try:
        return {
            "x0": float(rect.x0),
            "y0": float(rect.y0),
            "x1": float(rect.x1),
            "y1": float(rect.y1),
        }
    except Exception:
        return None


def _bbox_from_payload(payload: Any) -> Optional[Dict[str, float]]:
    if not isinstance(payload, dict):
        return None
    x0 = _safe_float(payload.get("x0"), float("nan"))
    y0 = _safe_float(payload.get("y0"), float("nan"))
    x1 = _safe_float(payload.get("x1"), float("nan"))
    y1 = _safe_float(payload.get("y1"), float("nan"))
    if any(v != v for v in (x0, y0, x1, y1)):  # NaN check
        return None
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


def _rect_area(bbox: Optional[Dict[str, float]]) -> float:
    if not bbox:
        return 0.0
    width = max(0.0, bbox["x1"] - bbox["x0"])
    height = max(0.0, bbox["y1"] - bbox["y0"])
    return width * height


def _rect_overlap(a: Optional[Dict[str, float]], b: Optional[Dict[str, float]]) -> float:
    if not a or not b:
        return 0.0
    ix0 = max(a["x0"], b["x0"])
    iy0 = max(a["y0"], b["y0"])
    ix1 = min(a["x1"], b["x1"])
    iy1 = min(a["y1"], b["y1"])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def _center_y(bbox: Optional[Dict[str, float]]) -> float:
    if not bbox:
        return 0.0
    return (bbox["y0"] + bbox["y1"]) * 0.5


def _figure_root() -> Path:
    configured = os.getenv("FIGURE_OUTPUT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_FIGURE_DIR


def _paper_dir(paper_id: int) -> Path:
    return _figure_root() / str(int(paper_id))


def _manifest_path(paper_id: int) -> Path:
    return _paper_dir(paper_id) / "manifest.json"


def _is_meaningful_image(width: int, height: int) -> bool:
    min_area = _safe_int(os.getenv("FIGURE_MIN_PIXEL_AREA", "4096"), 4096)
    min_side = _safe_int(os.getenv("FIGURE_MIN_SIDE_PX", "24"), 24)
    if width < min_side or height < min_side:
        return False
    return (width * height) >= max(1, min_area)


def _is_meaningful_render_rect(bbox: Optional[Dict[str, float]]) -> bool:
    if not bbox:
        return True
    width = max(0.0, float(bbox["x1"]) - float(bbox["x0"]))
    height = max(0.0, float(bbox["y1"]) - float(bbox["y0"]))
    min_side = _safe_float(os.getenv("FIGURE_MIN_RENDER_SIDE_PT", "18"), 18.0)
    min_area = _safe_float(os.getenv("FIGURE_MIN_RENDER_AREA", "800"), 800.0)
    if width < min_side or height < min_side:
        return False
    return (width * height) >= max(1.0, min_area)


def _prepare_page_blocks(blocks: Iterable[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    page_map: Dict[int, List[Dict[str, Any]]] = {}
    for block in blocks:
        page_no = _safe_int(block.get("page_no"), 0)
        if page_no <= 0:
            continue
        metadata = block.get("metadata")
        block_meta = metadata if isinstance(metadata, dict) else {}
        section_canonical = str(block_meta.get("section_canonical") or "").strip() or "other"
        section_title = str(block_meta.get("section_title") or "").strip() or "Document Body"
        section_source = str(block_meta.get("section_source") or "").strip() or "fallback"
        section_confidence = _safe_float(block_meta.get("section_confidence"), 0.35)
        page_map.setdefault(page_no, []).append(
            {
                "page_no": page_no,
                "block_index": _safe_int(block.get("block_index"), 0),
                "bbox": _bbox_from_payload(block.get("bbox")),
                "section_canonical": section_canonical,
                "section_title": section_title,
                "section_source": section_source,
                "section_confidence": section_confidence,
            }
        )
    for page_no, page_blocks in page_map.items():
        page_blocks.sort(key=lambda item: item.get("block_index", 0))
        page_map[page_no] = page_blocks
    return page_map


def _infer_section_for_image(
    page_blocks: List[Dict[str, Any]],
    image_bbox: Optional[Dict[str, float]],
) -> Dict[str, Any]:
    if not page_blocks:
        return {
            "section_canonical": "other",
            "section_title": "Document Body",
            "section_source": "fallback",
            "section_confidence": 0.25,
        }

    best_block: Optional[Dict[str, Any]] = None
    best_score = -1.0
    image_area = max(_rect_area(image_bbox), 1e-6)

    for block in page_blocks:
        block_bbox = block.get("bbox")
        overlap = _rect_overlap(image_bbox, block_bbox)
        score = 0.0
        if overlap > 0:
            block_area = max(_rect_area(block_bbox), 1e-6)
            overlap_ratio_image = overlap / image_area
            overlap_ratio_block = overlap / block_area
            score = (overlap_ratio_image * 0.8) + (overlap_ratio_block * 0.2)
        elif image_bbox and block_bbox:
            # If no overlap, prefer nearest block vertically on the same page.
            distance = abs(_center_y(image_bbox) - _center_y(block_bbox))
            score = 0.05 / (1.0 + distance)
        else:
            score = 0.01

        if score > best_score:
            best_score = score
            best_block = block

    if not best_block:
        return {
            "section_canonical": "other",
            "section_title": "Document Body",
            "section_source": "fallback",
            "section_confidence": 0.25,
        }

    inferred_confidence = max(
        0.25,
        min(
            0.98,
            _safe_float(best_block.get("section_confidence"), 0.35) * (0.8 + max(0.0, best_score)),
        ),
    )
    return {
        "section_canonical": str(best_block.get("section_canonical") or "other"),
        "section_title": str(best_block.get("section_title") or "Document Body"),
        "section_source": str(best_block.get("section_source") or "fallback"),
        "section_confidence": round(inferred_confidence, 3),
    }


def extract_and_store_paper_figures(
    pdf_path: Path,
    paper_id: int,
    blocks: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Extract embedded PDF figures for a paper and store a manifest mapped to sections.

    Returns a summary with extracted image count and manifest path.
    """
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    page_blocks = _prepare_page_blocks(blocks)
    output_dir = _paper_dir(paper_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale image files from previous extractions.
    for stale in output_dir.glob("page_*_img_*.*"):
        try:
            stale.unlink()
        except Exception:
            logger.warning("Failed to remove stale figure file %s", stale)

    records: List[Dict[str, Any]] = []
    doc = pymupdf.open(str(pdf_path))
    try:
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            page_no = page_index + 1
            images = page.get_images(full=True)
            for img_idx, image_info in enumerate(images, start=1):
                xref = _safe_int(image_info[0], -1)
                if xref <= 0:
                    continue
                try:
                    payload = doc.extract_image(xref)
                except Exception:
                    continue
                image_bytes = payload.get("image")
                if not image_bytes:
                    continue
                width = _safe_int(payload.get("width"), 0)
                height = _safe_int(payload.get("height"), 0)
                if width > 0 and height > 0 and not _is_meaningful_image(width, height):
                    continue

                ext = str(payload.get("ext") or "png").lower()
                file_name = f"page_{page_no:03d}_img_{img_idx:03d}.{ext}"
                image_path = output_dir / file_name
                with image_path.open("wb") as handle:
                    handle.write(image_bytes)

                rects = page.get_image_rects(xref) or []
                image_bbox = None
                if rects:
                    # Pick largest rendered rectangle for section assignment.
                    best_rect = max(rects, key=lambda rect: max(0.0, (rect.x1 - rect.x0)) * max(0.0, (rect.y1 - rect.y0)))
                    image_bbox = _bbox_from_rect(best_rect)
                if not _is_meaningful_render_rect(image_bbox):
                    continue

                section = _infer_section_for_image(page_blocks.get(page_no, []), image_bbox)
                records.append(
                    {
                        "id": len(records) + 1,
                        "paper_id": int(paper_id),
                        "page_no": page_no,
                        "file_name": file_name,
                        "image_path": str(image_path),
                        "url": f"/api/papers/{paper_id}/figures/{file_name}",
                        "width": width or None,
                        "height": height or None,
                        "bbox": image_bbox,
                        "section_canonical": section["section_canonical"],
                        "section_title": section["section_title"],
                        "section_source": section["section_source"],
                        "section_confidence": section["section_confidence"],
                    }
                )
    finally:
        doc.close()

    manifest = {
        "paper_id": int(paper_id),
        "source_pdf": str(pdf_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_images": len(records),
        "images": records,
    }
    manifest_path = _manifest_path(paper_id)
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    return {
        "paper_id": int(paper_id),
        "num_images": len(records),
        "manifest_path": str(manifest_path),
    }


def load_paper_figure_manifest(paper_id: int) -> Dict[str, Any]:
    path = _manifest_path(paper_id)
    if not path.exists():
        return {"paper_id": int(paper_id), "num_images": 0, "images": []}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        logger.warning("Failed to read figure manifest for paper %s: %s", paper_id, exc)
        return {"paper_id": int(paper_id), "num_images": 0, "images": []}
    if not isinstance(payload, dict):
        return {"paper_id": int(paper_id), "num_images": 0, "images": []}
    images = payload.get("images")
    if not isinstance(images, list):
        images = []
    payload["images"] = images
    payload["num_images"] = _safe_int(payload.get("num_images"), len(images))
    payload["paper_id"] = _safe_int(payload.get("paper_id"), int(paper_id))
    return payload


def resolve_figure_file(paper_id: int, file_name: str) -> Path:
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise ValueError("Invalid figure file name.")
    path = _paper_dir(paper_id) / safe_name
    return path
