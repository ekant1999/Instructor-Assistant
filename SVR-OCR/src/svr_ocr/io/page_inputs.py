from __future__ import annotations

import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from ..contracts import BlockType, PageImageBundle


@dataclass
class PageSeedOptions:
    block_type: BlockType = BlockType.PARAGRAPH
    confidence: float = 0.0
    difficulty: float = 0.7
    text_density: float = 1.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class MarginAwareSeedOptions:
    top_margin_ratio: float = 0.12
    bottom_margin_ratio: float = 0.12
    min_margin_px: int = 80
    max_margin_px: int = 260
    body_overlap_px: int = 16
    body_difficulty: float = 0.7
    body_text_density: float = 1.0
    margin_difficulty: float = 0.5
    margin_text_density: float = 0.4


def get_pdf_page_count(pdf_path: str | Path) -> int:
    command = ["pdfinfo", str(pdf_path)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo failed for {pdf_path}: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"Could not determine page count for {pdf_path}")


def get_pdf_media_box_width_height(pdf_path: str | Path, page_num: int) -> tuple[float, float]:
    command = ["pdfinfo", "-f", str(page_num), "-l", str(page_num), "-box", "-enc", "UTF-8", str(pdf_path)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo -box failed for {pdf_path}: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        if "MediaBox" in line:
            media_box = [float(x) for x in line.split(":", 1)[1].strip().split()]
            return abs(media_box[0] - media_box[2]), abs(media_box[3] - media_box[1])
    raise RuntimeError(f"MediaBox not found for {pdf_path} page {page_num}")


def render_pdf_page_to_png(
    pdf_path: str | Path,
    page_num: int,
    output_path: str | Path,
    *,
    target_longest_image_dim: int = 2048,
) -> Path:
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    media_width, media_height = get_pdf_media_box_width_height(pdf_path, page_num)
    longest_dim = max(media_width, media_height)
    dpi = max(72, int(target_longest_image_dim * 72 / max(longest_dim, 1.0)))
    prefix = output_path.with_suffix("")
    command = [
        "pdftoppm",
        "-png",
        "-singlefile",
        "-f",
        str(page_num),
        "-l",
        str(page_num),
        "-r",
        str(dpi),
        str(pdf_path),
        str(prefix),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed for {pdf_path} page {page_num}: {result.stderr.decode('utf-8', errors='replace').strip()}")
    rendered = output_path if output_path.exists() else prefix.with_suffix('.png')
    if not rendered.exists():
        raise RuntimeError(f"Expected rendered page image not found: {rendered}")
    return rendered


def get_png_dimensions(png_path: str | Path) -> tuple[int, int]:
    with open(png_path, 'rb') as fh:
        header = fh.read(24)
    if len(header) < 24 or header[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError(f"Not a valid PNG file: {png_path}")
    width, height = struct.unpack('>II', header[16:24])
    return width, height


def make_whole_page_bundle(
    image_path: str | Path,
    *,
    page_id: str,
    seed: PageSeedOptions | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> PageImageBundle:
    seed = seed or PageSeedOptions()
    image_path = Path(image_path)
    width, height = get_png_dimensions(image_path)
    metadata = {
        'blocks': [
            {
                'block_id': 'whole_page',
                'bbox': [0, 0, width, height],
                'block_type': seed.block_type.value,
                'order_index': 0,
                'layout_confidence': seed.confidence,
                'difficulty': seed.difficulty,
                'signals': {'text_density': seed.text_density},
                'metadata': {'seeded_whole_page': True, **seed.metadata},
            }
        ]
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return PageImageBundle(
        page_id=page_id,
        image_path=str(image_path),
        width=width,
        height=height,
        metadata=metadata,
    )


def make_margin_aware_page_bundle(
    image_path: str | Path,
    *,
    page_id: str,
    seed: MarginAwareSeedOptions | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> PageImageBundle:
    seed = seed or MarginAwareSeedOptions()
    image_path = Path(image_path)
    width, height = get_png_dimensions(image_path)
    top_h = _margin_height(
        height=height,
        ratio=seed.top_margin_ratio,
        min_margin_px=seed.min_margin_px,
        max_margin_px=seed.max_margin_px,
    )
    bottom_h = _margin_height(
        height=height,
        ratio=seed.bottom_margin_ratio,
        min_margin_px=seed.min_margin_px,
        max_margin_px=seed.max_margin_px,
    )
    overlap = max(0, int(seed.body_overlap_px))
    body_y0 = max(0, min(height - 1, top_h - overlap))
    body_y1 = min(height, max(body_y0 + 1, height - bottom_h + overlap))
    page_num = extra_metadata.get("page_num") if extra_metadata else None
    metadata = {
        'blocks': [
            _margin_block(
                block_id="top_margin",
                bbox=[0, 0, width, top_h],
                order_index=0,
                position_band="top",
                page_num=page_num,
                difficulty=seed.margin_difficulty,
                text_density=seed.margin_text_density,
            ),
            {
                'block_id': 'body',
                'bbox': [0, body_y0, width, body_y1],
                'block_type': BlockType.PARAGRAPH.value,
                'order_index': 1,
                'layout_confidence': 0.0,
                'difficulty': seed.body_difficulty,
                'signals': {'text_density': seed.body_text_density},
                'metadata': {
                    'seeded_margin_aware': True,
                    'position_band': 'body',
                    'drop_candidate': False,
                    'page_num': page_num,
                },
            },
            _margin_block(
                block_id="bottom_margin",
                bbox=[0, height - bottom_h, width, height],
                order_index=2,
                position_band="bottom",
                page_num=page_num,
                difficulty=seed.margin_difficulty,
                text_density=seed.margin_text_density,
            ),
        ]
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return PageImageBundle(
        page_id=page_id,
        image_path=str(image_path),
        width=width,
        height=height,
        metadata=metadata,
    )


def _margin_height(
    *,
    height: int,
    ratio: float,
    min_margin_px: int,
    max_margin_px: int,
) -> int:
    raw = int(height * ratio)
    clamped = min(max(raw, int(min_margin_px)), int(max_margin_px))
    return max(1, min(clamped, max(1, height // 2 - 1)))


def _margin_block(
    *,
    block_id: str,
    bbox: list[int],
    order_index: int,
    position_band: str,
    page_num: object,
    difficulty: float,
    text_density: float,
) -> dict[str, object]:
    return {
        'block_id': block_id,
        'bbox': bbox,
        'block_type': BlockType.HEADER_FOOTER.value,
        'order_index': order_index,
        'layout_confidence': 0.0,
        'difficulty': difficulty,
        'signals': {'text_density': text_density},
        'metadata': {
            'seeded_margin_aware': True,
            'position_band': position_band,
            'drop_candidate': True,
            'page_num': page_num,
        },
    }
