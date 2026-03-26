from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pymupdf
from PIL import Image, ImageDraw

import sys
ROOT = Path(__file__).resolve().parents[2]
PHASE1_SRC = ROOT / 'modules' / 'phase1-python' / 'src'
if str(PHASE1_SRC) not in sys.path:
    sys.path.insert(0, str(PHASE1_SRC))

from ia_phase1.parser import extract_text_blocks  # noqa: E402


def _load_manifest(paper_id: int) -> Dict[str, Any]:
    path = ROOT / '.ia_phase1_data' / 'figures' / str(int(paper_id)) / 'manifest.json'
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def _scale_bbox(bbox: Dict[str, Any], scale: float) -> tuple[float, float, float, float]:
    return (
        float(bbox['x0']) * scale,
        float(bbox['y0']) * scale,
        float(bbox['x1']) * scale,
        float(bbox['y1']) * scale,
    )


def _draw_text_box(draw: ImageDraw.ImageDraw, bbox: Dict[str, Any], *, scale: float, color: str, label: str) -> None:
    rect = _scale_bbox(bbox, scale)
    draw.rectangle(rect, outline=color, width=2)
    draw.text((rect[0] + 2, rect[1] + 2), label, fill=color)


def render_debug_overlays(
    *,
    paper_id: int,
    figure_ids: Iterable[int] | None = None,
    output_dir: Path,
) -> List[Path]:
    manifest = _load_manifest(paper_id)
    source_pdf = Path(manifest['source_pdf']).expanduser().resolve()
    figures = [item for item in manifest.get('images', []) if isinstance(item, dict)]
    if figure_ids:
        wanted = {int(item) for item in figure_ids}
        figures = [item for item in figures if int(item.get('id') or 0) in wanted]

    blocks = extract_text_blocks(source_pdf)
    by_page: Dict[int, List[Dict[str, Any]]] = {}
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get('bbox'), dict):
            continue
        by_page.setdefault(int(block.get('page_no') or 0), []).append(block)

    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Path] = []

    with pymupdf.open(str(source_pdf)) as doc:
        for figure in figures:
            page_no = int(figure.get('page_no') or 0)
            if page_no <= 0:
                continue
            page = doc.load_page(page_no - 1)
            scale = 2.0
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            image = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(image)

            figure_bbox = figure.get('bbox') if isinstance(figure.get('bbox'), dict) else None
            if figure_bbox:
                _draw_text_box(draw, figure_bbox, scale=scale, color='red', label=f"figure {figure.get('id')}")

            for block in by_page.get(page_no, []):
                bbox = block.get('bbox')
                if not isinstance(bbox, dict):
                    continue
                ix0 = max(float(bbox['x0']), float(figure_bbox['x0'])) if figure_bbox else 0
                iy0 = max(float(bbox['y0']), float(figure_bbox['y0'])) if figure_bbox else 0
                ix1 = min(float(bbox['x1']), float(figure_bbox['x1'])) if figure_bbox else 0
                iy1 = min(float(bbox['y1']), float(figure_bbox['y1'])) if figure_bbox else 0
                if not figure_bbox or ix1 <= ix0 or iy1 <= iy0:
                    continue
                label = ' '.join(str(block.get('text') or '').split())[:40]
                _draw_text_box(draw, bbox, scale=scale, color='blue', label=label)

            out_path = output_dir / f'paper_{paper_id}_figure_{int(figure.get("id") or 0):03d}_page_{page_no:03d}.png'
            image.save(out_path)
            results.append(out_path)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Render debug overlays for extracted figure regions.')
    parser.add_argument('--paper-id', type=int, required=True)
    parser.add_argument('--figure-id', type=int, action='append', dest='figure_ids')
    parser.add_argument('--output-dir', default=str(ROOT / '.ia_phase1_data' / 'figure_debug'))
    args = parser.parse_args()

    paths = render_debug_overlays(
        paper_id=args.paper_id,
        figure_ids=args.figure_ids,
        output_dir=Path(args.output_dir).expanduser().resolve(),
    )
    for path in paths:
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
