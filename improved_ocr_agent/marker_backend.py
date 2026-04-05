"""Thin wrapper around Marker's PdfConverter for the improved_ocr_agent pipeline.

Converts a PDF to markdown + extracted images, saving images into the existing
``_assets/`` directory structure expected by the rest of the pipeline.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_CONVERTER_SINGLETON: Optional["_ConverterCache"] = None


class _ConverterCache:
    """Lazy singleton so models are loaded once per process."""

    def __init__(self, *, force_ocr: bool = False, use_llm: bool = False):
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        config: Dict[str, Any] = {}
        if force_ocr:
            config["force_ocr"] = True
        if use_llm:
            config["use_llm"] = True

        kwargs: Dict[str, Any] = {"artifact_dict": create_model_dict()}
        if config:
            from marker.config.parser import ConfigParser

            config_parser = ConfigParser(config)
            kwargs["config"] = config_parser.generate_config_dict()
            if use_llm:
                kwargs["llm_service"] = config_parser.get_llm_service()

        self.converter = PdfConverter(**kwargs)

    def convert(self, pdf_path: str) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        from marker.output import text_from_rendered

        rendered = self.converter(pdf_path)
        text, metadata, images = text_from_rendered(rendered)
        return text, metadata, images


def get_converter(*, force_ocr: bool = False, use_llm: bool = False) -> _ConverterCache:
    """Return (and lazily create) the module-level converter singleton."""
    global _CONVERTER_SINGLETON
    if _CONVERTER_SINGLETON is None:
        _CONVERTER_SINGLETON = _ConverterCache(force_ocr=force_ocr, use_llm=use_llm)
    return _CONVERTER_SINGLETON


def reset_converter() -> None:
    """Drop the cached converter (useful in tests or when changing config)."""
    global _CONVERTER_SINGLETON
    _CONVERTER_SINGLETON = None


_IMAGE_REF_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")


def convert_pdf(
    pdf_path: str,
    *,
    output_dir: Optional[str] = None,
    force_ocr: bool = False,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """Convert *pdf_path* to markdown using Marker.

    Returns a dict with keys:
      - ``markdown``: the full markdown string
      - ``images``: list of saved image paths (relative to *output_dir*)
      - ``assets_dir``: absolute path to the assets directory
      - ``elapsed_ms``: conversion wall-time in milliseconds
    """
    pdf_path = os.path.abspath(pdf_path)
    pdf_name = Path(pdf_path).stem

    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    assets_dir = os.path.join(output_dir, f"{pdf_name}_assets")
    figure_dir = os.path.join(assets_dir, "figures")
    os.makedirs(figure_dir, exist_ok=True)

    converter = get_converter(force_ocr=force_ocr, use_llm=use_llm)

    start = time.perf_counter()
    text, _metadata, images = converter.convert(pdf_path)
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 3)

    saved_images: List[str] = []
    image_remap: Dict[str, str] = {}

    for image_name, image_obj in (images or {}).items():
        dest_path = os.path.join(figure_dir, image_name)
        try:
            image_obj.save(dest_path)
            rel = os.path.relpath(dest_path, output_dir).replace("\\", "/")
            saved_images.append(rel)
            image_remap[image_name] = rel
        except Exception:
            pass

    def _rewrite_image_ref(m: re.Match) -> str:
        src = m.group("src")
        if src in image_remap:
            return f"![{m.group('alt')}]({image_remap[src]})"
        return m.group(0)

    text = _IMAGE_REF_RE.sub(_rewrite_image_ref, text)

    return {
        "markdown": text,
        "images": saved_images,
        "assets_dir": assets_dir,
        "elapsed_ms": elapsed_ms,
    }
