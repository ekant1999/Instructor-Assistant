#!/usr/bin/env python3
"""
Generate paper chart figures as SVG assets using only the Python standard library.

Output files:
- internal_dataset_composition.svg
- internal_overall_system_comparison.svg
- internal_per_type_comparison.svg
- olmocr_backend_overall_comparison.svg
- olmocr_backend_category_breakdown.svg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import math
import xml.sax.saxutils as xml_utils


OUT_DIR = Path(__file__).resolve().parent


PALETTE = {
    "scholar_parser": "#1f4b7a",
    "ocr_agent": "#b55d2d",
    "improved_ocr_agent": "#2f6b3f",
    "qwen_structured": "#8c6d1f",
    "qwen_structured_post": "#5b7c99",
    "svr_ocr_full": "#2c7a7b",
    "olmocr2": "#8f2d56",
    "grid": "#d6dde5",
    "axis": "#24323f",
    "text": "#18222d",
    "muted": "#5a6875",
    "bg": "#ffffff",
}


@dataclass
class Series:
    name: str
    values: list[float]
    color: str
    errors: list[float] | None = None


def esc(text: str) -> str:
    return xml_utils.escape(text)


def fmt_metric(value: float, pct: bool = False) -> str:
    if pct:
        return f"{value:.1f}%"
    if value > 1 and abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3f}"


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<rect width="{width}" height="{height}" fill="{PALETTE["bg"]}"/>',
    ]


def svg_footer() -> list[str]:
    return ["</svg>"]


def add_text(
    items: list[str],
    x: float,
    y: float,
    text: str,
    *,
    size: int = 14,
    weight: str = "400",
    fill: str | None = None,
    anchor: str = "start",
) -> None:
    fill = fill or PALETTE["text"]
    items.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(text)}</text>'
    )


def add_line(
    items: list[str],
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str,
    width: float = 1.0,
    dash: str | None = None,
) -> None:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    items.append(
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'
    )


def add_rect(items: list[str], x: float, y: float, w: float, h: float, *, fill: str) -> None:
    items.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" rx="2" ry="2"/>'
    )


def compute_ticks(ymax: float, pct: bool) -> list[float]:
    if pct:
        return [0, 20, 40, 60, 80, 100]
    if ymax <= 1.01:
        return [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    step = math.ceil(ymax / 5)
    return [step * i for i in range(6)]


def draw_grouped_chart(
    items: list[str],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    categories: list[str],
    series: list[Series],
    ymax: float,
    pct: bool = False,
    annotate: bool = True,
) -> None:
    plot_left = x + 56
    plot_top = y + 28
    plot_width = width - 80
    plot_height = height - 80
    plot_bottom = plot_top + plot_height

    add_text(items, x, y + 12, title, size=16, weight="700")

    ticks = compute_ticks(ymax, pct)
    for tick in ticks:
        yy = plot_bottom - (tick / ymax) * plot_height
        add_line(items, plot_left, yy, plot_left + plot_width, yy, stroke=PALETTE["grid"], width=1)
        if pct:
            label = f"{int(tick)}"
        elif ymax <= 1.01:
            label = f"{tick:.1f}"
        else:
            label = f"{int(tick)}"
        add_text(items, plot_left - 10, yy + 4, label, size=11, fill=PALETTE["muted"], anchor="end")

    add_line(items, plot_left, plot_top, plot_left, plot_bottom, stroke=PALETTE["axis"], width=1.3)
    add_line(items, plot_left, plot_bottom, plot_left + plot_width, plot_bottom, stroke=PALETTE["axis"], width=1.3)

    group_count = len(categories)
    series_count = len(series)
    group_width = plot_width / group_count
    inner_width = group_width * 0.74
    bar_gap = inner_width * 0.08 / max(series_count - 1, 1)
    bar_width = (inner_width - bar_gap * max(series_count - 1, 0)) / series_count

    for i, category in enumerate(categories):
        gx = plot_left + group_width * i + (group_width - inner_width) / 2
        add_text(
            items,
            gx + inner_width / 2,
            plot_bottom + 24,
            category,
            size=12,
            fill=PALETTE["text"],
            anchor="middle",
        )
        for j, s in enumerate(series):
            value = s.values[i]
            bar_h = max(0.0, (value / ymax) * plot_height)
            bx = gx + j * (bar_width + bar_gap)
            by = plot_bottom - bar_h
            add_rect(items, bx, by, bar_width, bar_h, fill=s.color)
            if annotate:
                add_text(
                    items,
                    bx + bar_width / 2,
                    by - 6,
                    fmt_metric(value, pct=pct),
                    size=10,
                    fill=PALETTE["muted"],
                    anchor="middle",
                )
            if s.errors:
                err = s.errors[i]
                top_val = min(ymax, value + err)
                bot_val = max(0.0, value - err)
                y_top = plot_bottom - (top_val / ymax) * plot_height
                y_bot = plot_bottom - (bot_val / ymax) * plot_height
                cx = bx + bar_width / 2
                add_line(items, cx, y_top, cx, y_bot, stroke=PALETTE["axis"], width=1.2)
                add_line(items, cx - 5, y_top, cx + 5, y_top, stroke=PALETTE["axis"], width=1.2)
                add_line(items, cx - 5, y_bot, cx + 5, y_bot, stroke=PALETTE["axis"], width=1.2)


def draw_legend(items: list[str], x: float, y: float, series: Iterable[Series], *, columns: int = 3) -> None:
    series = list(series)
    col_width = 190
    row_height = 22
    for idx, s in enumerate(series):
        col = idx % columns
        row = idx // columns
        lx = x + col * col_width
        ly = y + row * row_height
        add_rect(items, lx, ly - 10, 14, 14, fill=s.color)
        add_text(items, lx + 22, ly + 1, s.name, size=12, fill=PALETTE["text"])


def write_svg(path: Path, items: list[str]) -> None:
    path.write_text("\n".join(items) + "\n", encoding="utf-8")


def build_internal_dataset_composition() -> None:
    width, height = 900, 520
    items = svg_header(width, height)
    add_text(items, 40, 36, "Internal Benchmark Dataset Composition", size=22, weight="700")
    add_text(items, 40, 60, "Expanded manually curated corpus used in the paper", size=13, fill=PALETTE["muted"])

    series = [Series("Documents", [40, 40, 40], PALETTE["improved_ocr_agent"])]
    draw_grouped_chart(
        items,
        x=40,
        y=86,
        width=820,
        height=370,
        title="Document counts by family",
        categories=["ResearchPapers", "Hybrid", "TextHeavy"],
        series=series,
        ymax=50,
        pct=False,
        annotate=True,
    )
    add_text(items, 40, 492, "Total corpus size: 120 PDFs", size=13, fill=PALETTE["muted"])
    write_svg(OUT_DIR / "internal_dataset_composition.svg", items + svg_footer())


def build_internal_overall() -> None:
    width, height = 1200, 640
    items = svg_header(width, height)
    add_text(items, 40, 36, "Internal Benchmark: Overall System Comparison", size=22, weight="700")
    add_text(items, 40, 60, "Expanded 120-document corpus", size=13, fill=PALETTE["muted"])

    systems = [
        Series("scholar_parser", [0.416], PALETTE["scholar_parser"]),
        Series("ocr_agent", [0.422], PALETTE["ocr_agent"]),
        Series("improved_ocr_agent", [0.509], PALETTE["improved_ocr_agent"]),
    ]
    draw_grouped_chart(
        items,
        x=40,
        y=96,
        width=540,
        height=430,
        title="Heading F1",
        categories=["Overall"],
        series=systems,
        ymax=1.0,
    )

    systems_anchor = [
        Series("scholar_parser", [0.309], PALETTE["scholar_parser"]),
        Series("ocr_agent", [0.450], PALETTE["ocr_agent"]),
        Series("improved_ocr_agent", [0.523], PALETTE["improved_ocr_agent"]),
    ]
    draw_grouped_chart(
        items,
        x=620,
        y=96,
        width=540,
        height=430,
        title="Anchor assignment accuracy",
        categories=["Overall"],
        series=systems_anchor,
        ymax=1.0,
    )

    draw_legend(items, 180, 566, [
        Series("scholar_parser", [], PALETTE["scholar_parser"]),
        Series("ocr_agent", [], PALETTE["ocr_agent"]),
        Series("improved_ocr_agent", [], PALETTE["improved_ocr_agent"]),
    ], columns=3)
    write_svg(OUT_DIR / "internal_overall_system_comparison.svg", items + svg_footer())


def build_internal_per_type() -> None:
    width, height = 1280, 700
    items = svg_header(width, height)
    add_text(items, 40, 36, "Internal Benchmark: Performance by Document Family", size=22, weight="700")
    add_text(items, 40, 60, "Per-type results on the expanded 120-document corpus", size=13, fill=PALETTE["muted"])

    categories = ["ResearchPapers", "Hybrid", "TextHeavy"]
    heading_series = [
        Series("scholar_parser", [0.684, 0.156, 0.407], PALETTE["scholar_parser"]),
        Series("ocr_agent", [0.371, 0.147, 0.748], PALETTE["ocr_agent"]),
        Series("improved_ocr_agent", [0.629, 0.150, 0.748], PALETTE["improved_ocr_agent"]),
    ]
    draw_grouped_chart(
        items,
        x=40,
        y=96,
        width=580,
        height=470,
        title="Heading F1 by document family",
        categories=categories,
        series=heading_series,
        ymax=1.0,
    )

    anchor_series = [
        Series("scholar_parser", [0.572, 0.127, 0.229], PALETTE["scholar_parser"]),
        Series("ocr_agent", [0.342, 0.152, 0.856], PALETTE["ocr_agent"]),
        Series("improved_ocr_agent", [0.560, 0.152, 0.856], PALETTE["improved_ocr_agent"]),
    ]
    draw_grouped_chart(
        items,
        x=660,
        y=96,
        width=580,
        height=470,
        title="Anchor assignment accuracy by document family",
        categories=categories,
        series=anchor_series,
        ymax=1.0,
    )

    draw_legend(items, 215, 612, [
        Series("scholar_parser", [], PALETTE["scholar_parser"]),
        Series("ocr_agent", [], PALETTE["ocr_agent"]),
        Series("improved_ocr_agent", [], PALETTE["improved_ocr_agent"]),
    ], columns=3)
    write_svg(OUT_DIR / "internal_per_type_comparison.svg", items + svg_footer())


def build_backend_overall() -> None:
    width, height = 980, 620
    items = svg_header(width, height)
    add_text(items, 40, 36, "olmOCR-Bench: Overall Backend Comparison", size=22, weight="700")
    add_text(items, 40, 60, "Official benchmark scores with reported confidence intervals", size=13, fill=PALETTE["muted"])

    series = [
        Series("qwen_structured", [50.0], PALETTE["qwen_structured"], [1.2]),
        Series("qwen_structured_post", [52.3], PALETTE["qwen_structured_post"], [1.2]),
        Series("svr_ocr_full", [72.8], PALETTE["svr_ocr_full"], [1.1]),
        Series("olmocr2", [74.7], PALETTE["olmocr2"], [1.0]),
    ]
    draw_grouped_chart(
        items,
        x=40,
        y=96,
        width=900,
        height=420,
        title="Average score on olmOCR-Bench",
        categories=["Benchmark score"],
        series=series,
        ymax=100.0,
        pct=True,
    )
    draw_legend(items, 100, 560, [
        Series("qwen_structured", [], PALETTE["qwen_structured"]),
        Series("qwen_structured_post", [], PALETTE["qwen_structured_post"]),
        Series("svr_ocr_full", [], PALETTE["svr_ocr_full"]),
        Series("olmocr2", [], PALETTE["olmocr2"]),
    ], columns=2)
    write_svg(OUT_DIR / "olmocr_backend_overall_comparison.svg", items + svg_footer())


def build_backend_category() -> None:
    width, height = 1220, 640
    items = svg_header(width, height)
    add_text(items, 40, 36, "olmOCR-Bench: Category Breakdown", size=22, weight="700")
    add_text(items, 40, 60, "Higher is better for every category", size=13, fill=PALETTE["muted"])

    categories = ["Absent", "Math", "Order", "Present", "Table"]
    series = [
        Series("qwen_structured_post", [66.3, 45.1, 38.4, 28.4, 44.3], PALETTE["qwen_structured_post"]),
        Series("svr_ocr_full", [42.3, 85.4, 70.7, 61.2, 78.2], PALETTE["svr_ocr_full"]),
        Series("olmocr2", [95.3, 72.5, 68.5, 51.5, 76.7], PALETTE["olmocr2"]),
    ]
    draw_grouped_chart(
        items,
        x=40,
        y=96,
        width=1140,
        height=450,
        title="Benchmark category scores",
        categories=categories,
        series=series,
        ymax=100.0,
        pct=True,
    )
    draw_legend(items, 270, 586, [
        Series("qwen_structured_post", [], PALETTE["qwen_structured_post"]),
        Series("svr_ocr_full", [], PALETTE["svr_ocr_full"]),
        Series("olmocr2", [], PALETTE["olmocr2"]),
    ], columns=3)
    write_svg(OUT_DIR / "olmocr_backend_category_breakdown.svg", items + svg_footer())


def main() -> None:
    build_internal_dataset_composition()
    build_internal_overall()
    build_internal_per_type()
    build_backend_overall()
    build_backend_category()
    print("Generated chart SVGs in", OUT_DIR)


if __name__ == "__main__":
    main()
