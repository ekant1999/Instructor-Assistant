from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..equations import extract_and_store_paper_equations, load_paper_equation_manifest
from ..figures import extract_and_store_paper_figures, load_paper_figure_manifest
from ..parser import extract_text_blocks
from ..sectioning import KNOWN_CANONICALS, annotate_blocks_with_sections, canonicalize_heading
from ..tables import extract_and_store_paper_tables, load_paper_table_manifest
from .bundle import prepare_asset_bundle
from .models import MarkdownExportConfig, MarkdownExportResult


def export_pdf_to_markdown(
    pdf_path: str | Path,
    *,
    paper_id: int,
    output_dir: str | Path | None = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    source_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[MarkdownExportConfig] = None,
) -> MarkdownExportResult:
    config = config or MarkdownExportConfig()
    pdf_path = Path(pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    bundle_dir = _resolve_bundle_dir(paper_id, output_dir)
    _prepare_bundle_dir(bundle_dir, overwrite=config.overwrite)

    working_blocks = deepcopy(blocks) if blocks is not None else extract_text_blocks(pdf_path)
    _ensure_section_metadata(working_blocks, pdf_path=pdf_path, source_url=source_url)

    if config.ensure_assets:
        extract_and_store_paper_figures(pdf_path, paper_id=paper_id, blocks=working_blocks)
        extract_and_store_paper_tables(pdf_path, paper_id=paper_id, blocks=working_blocks)
        extract_and_store_paper_equations(pdf_path, paper_id=paper_id, blocks=working_blocks)

    figure_manifest = load_paper_figure_manifest(paper_id)
    table_manifest = load_paper_table_manifest(paper_id)
    equation_manifest = load_paper_equation_manifest(paper_id)
    bundled_assets = prepare_asset_bundle(
        paper_id=paper_id,
        bundle_dir=bundle_dir,
        figure_manifest=figure_manifest,
        table_manifest=table_manifest,
        equation_manifest=equation_manifest,
        config=config,
    )
    _realign_asset_sections(blocks=working_blocks, bundled_assets=bundled_assets)

    final_metadata = _build_metadata(
        pdf_path=pdf_path,
        paper_id=paper_id,
        source_url=source_url,
        blocks=working_blocks,
        metadata=metadata,
        asset_counts=bundled_assets["asset_counts"],
    )
    markdown = render_markdown_document(
        blocks=working_blocks,
        bundled_assets=bundled_assets,
        metadata=final_metadata,
        config=config,
    )

    markdown_path = bundle_dir / "paper.md"
    markdown_path.write_text(markdown, encoding="utf-8")

    manifest_payload = {
        "paper_id": int(paper_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_pdf": str(pdf_path),
        "markdown_file": markdown_path.name,
        "metadata": final_metadata,
        "config": asdict(config),
        "asset_counts": bundled_assets["asset_counts"],
        "sections": _section_summary(working_blocks),
        "assets": {
            "figures": [_manifest_asset_view(item, ["id", "page_no", "file_name", "figure_type", "figure_number", "figure_body", "figure_caption", "section_canonical", "markdown_path"]) for item in bundled_assets["figures"]],
            "tables": [_manifest_asset_view(item, ["id", "page_no", "json_file", "caption", "section_canonical", "markdown_json_path"]) for item in bundled_assets["tables"]],
            "equations": [_manifest_asset_view(item, ["id", "page_no", "equation_number", "file_name", "json_file", "section_canonical", "latex", "latex_source", "latex_confidence", "render_mode", "markdown_image_path", "markdown_json_path"]) for item in bundled_assets["equations"]],
        },
    }
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return MarkdownExportResult(
        paper_id=int(paper_id),
        bundle_dir=bundle_dir,
        markdown_path=markdown_path,
        manifest_path=manifest_path,
        markdown=markdown,
        asset_counts=bundled_assets["asset_counts"],
        metadata={key: str(value) for key, value in final_metadata.items() if value is not None},
        section_count=len(manifest_payload["sections"]),
    )


def render_markdown_document(
    *,
    blocks: List[Dict[str, Any]],
    bundled_assets: Dict[str, Any],
    metadata: Dict[str, Any],
    config: MarkdownExportConfig,
) -> str:
    lines: List[str] = []
    if config.include_frontmatter:
        lines.extend(_render_frontmatter(metadata))
        lines.append("")

    render_assets = _filter_bundled_assets_for_markdown(blocks=blocks, bundled_assets=bundled_assets)
    render_state_assets = dict(render_assets)
    render_state_assets["figures"] = [
        item for item in bundled_assets.get("figures", []) if isinstance(item, dict)
    ]
    render_state = _build_render_state(blocks=blocks, bundled_assets=render_state_assets, metadata=metadata)
    events = _compose_events(blocks, render_assets)
    current_section: Optional[str] = None
    current_page: Optional[int] = None
    current_subheading: Optional[Tuple[str, int]] = None

    for event in events:
        page_no = int(event.get("page_no") or 0)
        rendered_lines: List[str] = []

        if event["kind"] == "text":
            block = event["block"]
            text = str(block.get("text") or "").strip()
            structural_heading = _parse_structural_heading_block(text, block=block)
            if structural_heading:
                if config.include_page_markers and page_no and page_no != current_page:
                    if lines and lines[-1] != "":
                        lines.append("")
                    lines.append(f"<!-- page:{page_no} -->")
                    lines.append("")
                current_page = page_no or current_page
                if structural_heading["level"] <= 2:
                    if current_section != structural_heading["canonical"]:
                        if lines and lines[-1] != "":
                            lines.append("")
                        lines.append(f"## {structural_heading['title']}")
                        lines.append("")
                        current_section = structural_heading["canonical"]
                        current_subheading = None
                    continue
                subheading_key = (structural_heading["title"], int(structural_heading["level"]))
                if current_subheading != subheading_key:
                    if lines and lines[-1] != "":
                        lines.append("")
                    lines.append(f"{'#' * structural_heading['level']} {structural_heading['title']}")
                    lines.append("")
                    current_subheading = subheading_key
                continue
            if _should_skip_block_text(block, bundled_assets=render_assets, render_state=render_state):
                continue
            if text:
                rendered_text = _normalize_block_text_for_markdown(block=block, text=text, render_state=render_state)
                rendered_lines.extend([_escape_markdown_text(rendered_text), ""])
        else:
            rendered_lines.extend(_render_asset_event(event, config=config))
            if rendered_lines and rendered_lines[-1] != "":
                rendered_lines.append("")
        if not rendered_lines:
            continue

        if config.include_page_markers and page_no and page_no != current_page:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"<!-- page:{page_no} -->")
            lines.append("")
        current_page = page_no or current_page

        section_canonical = str(event.get("section_canonical") or "other").strip() or "other"
        section_title = str(event.get("section_title") or "Document Body").strip() or "Document Body"
        if section_canonical != current_section and section_canonical != "front_matter":
            if lines and lines[-1] != "":
                lines.append("")
            heading_level = max(2, min(6, int(event.get("section_level") or 2)))
            lines.append(f"{'#' * heading_level} {section_title}")
            lines.append("")
            current_section = section_canonical
            current_subheading = None
        elif current_section is None:
            current_section = section_canonical

        lines.extend(rendered_lines)

    markdown = "\n".join(lines).strip() + "\n"
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = _postprocess_rendered_markdown(markdown, metadata=metadata)
    return markdown


def _compose_events(blocks: List[Dict[str, Any]], bundled_assets: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    page_block_entries: Dict[int, List[Tuple[int, Dict[str, Any]]]] = defaultdict(list)
    for order, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        page_no = _safe_int(block.get("page_no"), 0)
        if page_no > 0:
            page_block_entries[page_no].append((order, block))
        events.append(
            {
                "kind": "text",
                "page_no": page_no,
                "sort_order": float(order),
                "section_canonical": _event_section_value(block, "section_canonical", default="other"),
                "section_title": _event_section_value(block, "section_title", default="Document Body"),
                "section_level": _safe_int(_event_section_value(block, "section_level", default=2), 2),
                "block": block,
            }
        )

    for figure in bundled_assets.get("figures", []):
        events.append(_asset_event("figure", figure, page_block_entries=page_block_entries, default_order=len(blocks)))
    for table in bundled_assets.get("tables", []):
        events.append(_asset_event("table", table, page_block_entries=page_block_entries, default_order=len(blocks)))
    for equation in bundled_assets.get("equations", []):
        events.append(_asset_event("equation", equation, page_block_entries=page_block_entries, default_order=len(blocks)))

    events.sort(key=lambda item: (item["page_no"], item["sort_order"], str(item.get("kind") or "")))
    return events


def _asset_event(
    kind: str,
    record: Dict[str, Any],
    *,
    page_block_entries: Dict[int, List[Tuple[int, Dict[str, Any]]]],
    default_order: int,
) -> Dict[str, Any]:
    page_no = _safe_int(record.get("page_no"), 0)
    sort_order = _asset_sort_order(kind, record, page_block_entries=page_block_entries, default_order=default_order)
    section_canonical = str(record.get("section_canonical") or "other")
    section_title = str(record.get("section_title") or "Document Body")
    section_level = 2
    previous_section = _nearest_page_block_section(page_block_entries.get(page_no) or [], sort_order=sort_order, direction="previous")
    next_section = _nearest_page_block_section(page_block_entries.get(page_no) or [], sort_order=sort_order, direction="next")
    if (
        previous_section
        and next_section
        and previous_section[0] == next_section[0]
        and previous_section[0] not in {"front_matter", "other"}
    ):
        section_canonical, section_title, section_level = previous_section
    elif section_canonical in {"front_matter", "other"}:
        neighbor_section = previous_section or next_section
        if neighbor_section and neighbor_section[0] not in {"front_matter", "other"}:
            section_canonical, section_title, section_level = neighbor_section
    return {
        "kind": kind,
        "page_no": page_no,
        "sort_order": sort_order,
        "section_canonical": section_canonical,
        "section_title": section_title,
        "section_level": section_level,
        "record": record,
    }


def _nearest_page_block_section(
    page_entries: List[Tuple[int, Dict[str, Any]]],
    *,
    sort_order: float,
    direction: str,
) -> Optional[Tuple[str, str, int]]:
    if direction == "previous":
        entries = reversed(page_entries)
        predicate = lambda order: float(order) <= sort_order + 1e-6
    else:
        entries = iter(page_entries)
        predicate = lambda order: float(order) > sort_order + 1e-6

    for order, block in entries:
        if not predicate(order):
            continue
        section_canonical = str(_event_section_value(block, "section_canonical", default="other") or "other")
        section_title = str(_event_section_value(block, "section_title", default="Document Body") or "Document Body")
        section_level = _safe_int(_event_section_value(block, "section_level", default=2), 2)
        return section_canonical, section_title, section_level
    return None


def _asset_sort_order(
    kind: str,
    record: Dict[str, Any],
    *,
    page_block_entries: Dict[int, List[Tuple[int, Dict[str, Any]]]],
    default_order: int,
) -> float:
    page_no = _safe_int(record.get("page_no"), 0)
    page_entries = page_block_entries.get(page_no) or []
    if not page_entries:
        return float(default_order + max(page_no, 0)) + _asset_order_offset(kind)

    anchor_orders: List[int] = []
    if kind == "figure":
        caption_anchor_orders = [
            order for order, block in page_entries if _block_matches_asset_caption(block, record, caption_key="figure_caption")
        ]
        if caption_anchor_orders:
            return float(min(caption_anchor_orders)) - 0.25 + _asset_order_offset(kind)
        anchor_orders = [order for order, block in page_entries if _block_owned_by_asset(block, record, caption_key="figure_caption")]
    elif kind == "table":
        caption_anchor_orders = [
            order for order, block in page_entries if _block_matches_asset_caption(block, record, caption_key="caption")
        ]
        if caption_anchor_orders:
            return float(min(caption_anchor_orders)) - 0.24 + _asset_order_offset(kind)
        anchor_orders = [order for order, block in page_entries if _block_owned_by_asset(block, record, caption_key="caption")]
    elif kind == "equation":
        anchor_orders = [order for order, block in page_entries if _block_matches_equation_asset(block, record)]
    if anchor_orders:
        return float(min(anchor_orders)) - 0.25 + _asset_order_offset(kind)

    asset_bbox = record.get("bbox") if isinstance(record.get("bbox"), dict) else {}
    asset_y0 = _bbox_coord(asset_bbox, "y0")
    for order, block in page_entries:
        block_y0 = _bbox_coord(block.get("bbox"), "y0")
        if block_y0 >= asset_y0 - 4.0:
            return float(order) - 0.1 + _asset_order_offset(kind)
    return float(page_entries[-1][0]) + 0.75 + _asset_order_offset(kind)


def _asset_order_offset(kind: str) -> float:
    return {
        "figure": 0.00,
        "table": 0.01,
        "equation": 0.02,
    }.get(kind, 0.03)


def _block_matches_asset_caption(block: Dict[str, Any], asset: Dict[str, Any], *, caption_key: str) -> bool:
    block_page = _safe_int(block.get("page_no"), 0)
    asset_page = _safe_int(asset.get("page_no"), 0)
    if block_page <= 0 or asset_page <= 0 or block_page != asset_page:
        return False

    caption = str(asset.get(caption_key) or "").strip()
    block_text = str(block.get("text") or "").strip()
    if not caption or not block_text:
        return False

    normalized_caption = _normalize_caption_text(caption)
    normalized_block = _normalize_caption_text(block_text)
    if not normalized_caption or not normalized_block:
        return False
    if not (normalized_block.startswith(normalized_caption) or normalized_caption.startswith(normalized_block)):
        return False

    block_bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    asset_bbox = asset.get("bbox") if isinstance(asset.get("bbox"), dict) else {}
    if not block_bbox or not asset_bbox:
        return False

    block_y0 = _bbox_coord(block_bbox, "y0")
    block_y1 = _bbox_coord(block_bbox, "y1")
    asset_y0 = _bbox_coord(asset_bbox, "y0")
    asset_y1 = _bbox_coord(asset_bbox, "y1")
    vertical_gap = min(abs(block_y0 - asset_y1), abs(asset_y0 - block_y1))
    x_overlap = _x_overlap_ratio(block_bbox, asset_bbox)
    return vertical_gap <= 72.0 and x_overlap >= 0.12


def _block_matches_equation_asset(block: Dict[str, Any], record: Dict[str, Any]) -> bool:
    block_page = _safe_int(block.get("page_no"), 0)
    asset_page = _safe_int(record.get("page_no"), 0)
    if block_page <= 0 or asset_page <= 0 or block_page != asset_page:
        return False

    block_bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    asset_bbox = record.get("bbox") if isinstance(record.get("bbox"), dict) else {}
    if not block_bbox or not asset_bbox:
        return False

    overlap = _rect_overlap(block_bbox, asset_bbox)
    block_area = _rect_area(block_bbox)
    if block_area > 0 and overlap / block_area >= 0.2:
        return True
    if _point_in_bbox(_bbox_center(block_bbox), _expand_bbox(asset_bbox, margin_x=18.0, margin_y=12.0)):
        return True
    return False


def _render_asset_event(event: Dict[str, Any], *, config: MarkdownExportConfig) -> List[str]:
    kind = str(event.get("kind") or "")
    record = event.get("record") or {}
    lines: List[str] = []
    if kind == "figure":
        figure_number = _figure_display_number(record)
        alt = f"Figure {figure_number}".strip() if figure_number else "Figure"
        markdown_path = str(record.get("markdown_path") or "").strip()
        caption = _figure_caption_line(record)
        if markdown_path:
            lines.append(f"![{alt}]({markdown_path})")
        if caption:
            if markdown_path:
                lines.append("")
            if figure_number:
                lines.append(f"_Figure {figure_number}: {caption}_")
            else:
                lines.append(f"_{caption}_")
        return lines or [f"<!-- missing figure asset for page {record.get('page_no')} -->"]
    if kind == "table":
        caption = str(record.get("caption") or "").strip()
        json_path = str(record.get("markdown_json_path") or "").strip()
        if json_path:
            lines.append(f"> Table JSON: `{json_path}`")
        if caption:
            lines.append(f"> {_table_caption_line(record)}")
        return lines or [f"<!-- missing table asset for page {record.get('page_no')} -->"]
    if kind == "equation":
        eq_id = record.get("equation_number") or record.get("id") or ""
        latex = str(record.get("latex") or "").strip()
        json_path = str(record.get("markdown_json_path") or "").strip()
        image_path = str(record.get("markdown_image_path") or "").strip()
        if config.prefer_equation_latex and latex:
            lines.append("$$")
            lines.append(latex)
            lines.append("$$")
        include_fallback_assets = config.include_equation_fallback_assets or not latex
        if json_path:
            if include_fallback_assets:
                lines.append(f"> Equation {eq_id} JSON: `{json_path}`")
        if image_path:
            if include_fallback_assets:
                lines.append(f"> Equation {eq_id} image: `{image_path}`")
        return lines or [f"<!-- missing equation asset for page {record.get('page_no')} -->"]
    return []


def _render_frontmatter(metadata: Dict[str, Any]) -> List[str]:
    lines = ["---"]
    for key in [
        "title",
        "paper_id",
        "source_pdf",
        "source_url",
        "generated_at",
        "num_figures",
        "num_tables",
        "num_equations",
    ]:
        value = metadata.get(key)
        if value is None or value == "":
            continue
        lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return lines


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _escape_markdown_text(text: str) -> str:
    return str(text or "").replace("#", r"\#")


def _normalize_block_text_for_markdown(
    *,
    block: Dict[str, Any],
    text: str,
    render_state: Dict[str, Any],
) -> str:
    raw_text = str(text or "")
    if "\n" not in raw_text:
        return raw_text.strip()

    compact = " ".join(raw_text.split()).strip()
    if not compact:
        return ""
    if _looks_like_table_caption(compact) or _parse_figure_caption(compact):
        return raw_text.strip()
    if _looks_like_section_boundary_block(compact) or _looks_like_visual_label_text(compact):
        return raw_text.strip()
    if _looks_like_front_matter_name_block(compact) or _looks_like_front_matter_author_block(compact):
        return raw_text.strip()
    if _is_front_matter_metadata_block(block, text=compact):
        return raw_text.strip()
    if not _should_reflow_block_text(block=block, compact=compact, raw_text=raw_text, render_state=render_state):
        return raw_text.strip()

    paragraphs: List[str] = []
    for chunk in re.split(r"\n\s*\n", raw_text):
        lines = [_normalize_inline_whitespace(line) for line in chunk.splitlines() if _normalize_inline_whitespace(line)]
        if not lines:
            continue
        merged = lines[0]
        for next_line in lines[1:]:
            if _should_dehyphenate_line_break(merged, next_line):
                merged = merged.rstrip()[:-1] + next_line.lstrip()
            else:
                merged = f"{merged.rstrip()} {next_line.lstrip()}".strip()
        paragraphs.append(merged.strip())

    return "\n\n".join(paragraphs).strip() if paragraphs else raw_text.strip()


def _normalize_inline_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _should_dehyphenate_line_break(current: str, next_line: str) -> bool:
    stripped_current = str(current or "").rstrip()
    stripped_next = str(next_line or "").lstrip()
    if len(stripped_current) < 2 or not stripped_next:
        return False
    if stripped_current[-1] not in "-‐‑‒–":
        return False
    if not stripped_current[-2].isalpha():
        return False
    first_next = stripped_next[0]
    return first_next.isalpha() and first_next.islower()


def _should_reflow_block_text(
    *,
    block: Dict[str, Any],
    compact: str,
    raw_text: str,
    render_state: Dict[str, Any],
) -> bool:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    line_count = _safe_int(metadata.get("line_count"), len([line for line in raw_text.splitlines() if line.strip()]))
    if line_count <= 1:
        return False
    if _is_front_matter_narrative_block(block, text=compact, render_state=render_state):
        return True
    if _looks_like_sentenceish_prose(compact):
        return True

    lines = [_normalize_inline_whitespace(line) for line in raw_text.splitlines() if _normalize_inline_whitespace(line)]
    if len(lines) < 2:
        return False
    alpha_words = len(re.findall(r"[A-Za-z]{2,}", compact))
    long_lines = sum(1 for line in lines if len(line) >= 28)
    if alpha_words >= 12 and long_lines >= 2:
        return True
    if any(_should_dehyphenate_line_break(lines[idx], lines[idx + 1]) for idx in range(len(lines) - 1)):
        return True
    return False


def _figure_display_number(record: Dict[str, Any]) -> str:
    figure_number = str(record.get("figure_number") or "").strip()
    if figure_number:
        return figure_number
    caption = str(record.get("figure_caption") or "").strip()
    parsed = _parse_figure_caption(caption)
    if parsed:
        return parsed["number"]
    return ""


def _figure_caption_line(record: Dict[str, Any]) -> str:
    body = str(record.get("figure_body") or "").strip()
    if body:
        return body
    caption = str(record.get("figure_caption") or "").strip()
    if not caption:
        return ""
    parsed = _parse_figure_caption(caption)
    if parsed:
        return parsed["body"]
    return caption


def _parse_figure_caption(text: str) -> Optional[Dict[str, str]]:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return None
    match = re.match(
        r"^\s*(?P<label>figure|fig\.?)\s*(?P<number>\d+[A-Za-z]?)\s*(?:[:.\-])\s*(?P<body>.+?)\s*$",
        compact,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    number = str(match.group("number") or "").strip()
    body = str(match.group("body") or "").strip()
    if not number or not body:
        return None
    return {"number": number, "body": body}


def _table_caption_line(record: Dict[str, Any]) -> str:
    caption = str(record.get("caption") or "").strip()
    if caption and _looks_like_table_caption(caption):
        return caption
    table_id = record.get("id")
    if caption:
        return f"Table {table_id}: {caption}"
    return f"Table {table_id}"


def _table_caption_key(caption: str) -> str:
    compact = " ".join(str(caption or "").split()).strip()
    if not compact:
        return ""
    match = re.match(r"^(table\s+\d+[A-Za-z]?)\b", compact, flags=re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return re.sub(r"[^a-z0-9]+", " ", compact.lower()).strip()[:120]


_STRUCTURAL_HEADING_RE = re.compile(
    r"^\s*(?P<num>(?:[A-Z](?:\.\d+){0,3}|\d+(?:\.\d+){0,3}|[IVXLCDM]+))\.?\s+(?P<title>[A-Z].{0,180})\s*$"
)


def _parse_structural_heading_block(text: str, *, block: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return None
    if _looks_like_table_caption(compact) or _parse_figure_caption(compact):
        return None

    metadata = block.get("metadata") if isinstance(block, dict) and isinstance(block.get("metadata"), dict) else {}
    line_count = _safe_int(metadata.get("line_count"), max(1, len(str(text or "").splitlines())))
    char_count = _safe_int(metadata.get("char_count"), len(compact))
    max_font_size = _safe_float(metadata.get("max_font_size"), 0.0)
    if line_count > 3 or char_count > 180:
        return None

    number = ""
    title = ""
    match = _STRUCTURAL_HEADING_RE.match(compact)
    if match:
        number = str(match.group("num") or "").strip()
        title = str(match.group("title") or "").strip(" .:-")
    else:
        if compact.rstrip().endswith("."):
            return None
        if max_font_size < 10.0 and (line_count > 1 or char_count > 90):
            return None
        normalized = canonicalize_heading(compact)
        if normalized not in KNOWN_CANONICALS or normalized in {"front_matter", "other"}:
            return None
        title = compact.strip(" .:-")

    if not title:
        return None
    if re.search(r"\b(university|institute|laborator(?:y|ies)|school|department|college|technologies|labs?)\b", title.lower()):
        return None
    if _looks_like_sentenceish_prose(compact) and max_font_size < 10.0:
        return None
    if len(title.split()) > 16:
        return None

    canonical = canonicalize_heading(title)
    if not canonical or canonical == "other":
        canonical = canonicalize_heading(compact)

    level = 2
    if number:
        depth = number.count(".")
        level = min(6, 2 + depth)
    if canonical == "appendix" and number:
        level = max(level, 2)
    metadata_level = _safe_int(metadata.get("section_level"), 0)
    if metadata_level > 0:
        level = max(2, min(6, metadata_level))

    return {
        "number": number,
        "title": title,
        "canonical": canonical,
        "level": level,
    }


def _realign_sections_from_structural_headings(blocks: List[Dict[str, Any]]) -> None:
    if not blocks:
        return

    page_entries: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        if isinstance(block, dict):
            page_entries[_safe_int(block.get("page_no"), 0)].append(block)

    for page_no, page_blocks in page_entries.items():
        active_top_heading: Optional[Dict[str, Any]] = None
        heading_y0 = 0.0
        for block in page_blocks:
            text = str(block.get("text") or "").strip()
            if not text:
                continue
            parsed = _parse_structural_heading_block(text, block=block)
            metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
            bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
            if parsed:
                metadata["section_canonical"] = parsed["canonical"]
                metadata["section_title"] = parsed["title"]
                metadata["section_level"] = parsed["level"]
                metadata["section_source"] = "structural_heading"
                metadata["section_confidence"] = max(0.9, _safe_float(metadata.get("section_confidence"), 0.0))
                if parsed["level"] <= 2:
                    active_top_heading = parsed
                    heading_y0 = _bbox_coord(bbox, "y0")
                continue

            if not active_top_heading or page_no <= 0 or not bbox:
                continue

            current_canonical = str(metadata.get("section_canonical") or "")
            current_title = str(metadata.get("section_title") or "")
            compact = " ".join(text.split()).strip()
            if _looks_like_table_caption(compact) or _parse_figure_caption(compact):
                continue
            if compact.startswith(("⋆", "†", "*", "‡")) and len(compact) <= 120:
                continue
            if current_canonical not in {"", "front_matter", "abstract", "other"}:
                continue
            if _bbox_coord(bbox, "y0") < heading_y0 - 2.0:
                continue
            if len(compact) < 60 and not _looks_like_sentenceish_prose(compact):
                continue
            if current_title and current_title == active_top_heading["title"]:
                continue

            metadata["section_canonical"] = active_top_heading["canonical"]
            metadata["section_title"] = active_top_heading["title"]
            metadata["section_level"] = max(2, active_top_heading["level"])
            metadata["section_source"] = "structural_heading_propagated"
            metadata["section_confidence"] = max(0.82, _safe_float(metadata.get("section_confidence"), 0.0))


def _ensure_section_metadata(blocks: List[Dict[str, Any]], *, pdf_path: Path, source_url: Optional[str]) -> None:
    annotate_blocks_with_sections(blocks=blocks, pdf_path=pdf_path, source_url=source_url)
    _realign_sections_from_structural_headings(blocks)


def _build_metadata(
    *,
    pdf_path: Path,
    paper_id: int,
    source_url: Optional[str],
    blocks: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
    asset_counts: Dict[str, int],
) -> Dict[str, Any]:
    payload = dict(metadata or {})
    payload.setdefault("title", pdf_path.stem)
    payload.setdefault("paper_id", int(paper_id))
    payload.setdefault("source_pdf", str(pdf_path))
    if source_url:
        payload.setdefault("source_url", source_url)
    payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    payload.setdefault("num_figures", int(asset_counts.get("figures", 0)))
    payload.setdefault("num_tables", int(asset_counts.get("tables", 0)))
    payload.setdefault("num_equations", int(asset_counts.get("equations", 0)))
    if blocks:
        payload.setdefault("page_count", max(_safe_int(block.get("page_no"), 1) for block in blocks if isinstance(block, dict)))
    return payload


def _section_summary(blocks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for block in blocks:
        if not isinstance(block, dict):
            continue
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        canonical = str(metadata.get("section_canonical") or "other")
        index = _safe_int(metadata.get("section_index"), 0)
        key = (canonical, index)
        if key in seen:
            continue
        seen.add(key)
        summaries.append(
            {
                "section_index": index,
                "section_canonical": canonical,
                "section_title": str(metadata.get("section_title") or "Document Body"),
                "page_no": _safe_int(block.get("page_no"), 1),
            }
        )
    return summaries


def _event_section_value(event: Dict[str, Any], key: str, *, default: Any) -> Any:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    value = metadata.get(key)
    return default if value in (None, "") else value


def _bbox_coord(bbox: Any, key: str) -> float:
    if isinstance(bbox, dict):
        try:
            return float(bbox.get(key, 0.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


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


def _page_bounds_for_blocks(blocks: Iterable[Dict[str, Any]]) -> Dict[int, Tuple[float, float, float, float]]:
    page_boxes: Dict[int, List[float]] = {}
    for block in blocks:
        if not isinstance(block, dict):
            continue
        page_no = _safe_int(block.get("page_no"), 0)
        bbox = block.get("bbox")
        if page_no <= 0 or not isinstance(bbox, dict):
            continue
        x0 = _bbox_coord(bbox, "x0")
        y0 = _bbox_coord(bbox, "y0")
        x1 = _bbox_coord(bbox, "x1")
        y1 = _bbox_coord(bbox, "y1")
        if page_no not in page_boxes:
            page_boxes[page_no] = [x0, y0, x1, y1]
            continue
        agg = page_boxes[page_no]
        agg[0] = min(agg[0], x0)
        agg[1] = min(agg[1], y0)
        agg[2] = max(agg[2], x1)
        agg[3] = max(agg[3], y1)
    return {page_no: (vals[0], vals[1], vals[2], vals[3]) for page_no, vals in page_boxes.items()}


def _line_signature(value: str) -> str:
    text = " ".join(str(value or "").split()).strip().lower()
    text = re.sub(r"[^a-z0-9:/\.\- ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _build_render_state(
    *,
    blocks: List[Dict[str, Any]],
    bundled_assets: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    line_counts: Counter[str] = Counter()
    for block in blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        for line in text.splitlines():
            signature = _line_signature(line)
            if signature:
                line_counts[signature] += 1

    figure_page_stats: Dict[int, Dict[str, int]] = defaultdict(lambda: {"embedded": 0, "vector_with_caption": 0})
    figure_bboxes_by_page: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for figure in bundled_assets.get("figures", []):
        if not isinstance(figure, dict):
            continue
        page_no = _safe_int(figure.get("page_no"), 0)
        if page_no <= 0:
            continue
        bbox = figure.get("bbox") if isinstance(figure.get("bbox"), dict) else None
        if bbox:
            figure_bboxes_by_page[page_no].append(
                {
                    "bbox": bbox,
                    "figure_type": str(figure.get("figure_type") or ""),
                    "caption": str(figure.get("figure_caption") or "").strip(),
                }
            )
        if str(figure.get("figure_type") or "") == "embedded":
            figure_page_stats[page_no]["embedded"] += 1
        if str(figure.get("figure_type") or "") == "vector" and str(figure.get("figure_caption") or "").strip():
            figure_page_stats[page_no]["vector_with_caption"] += 1

    table_regions = _infer_table_regions(blocks)
    return {
        "page_bounds": _page_bounds_for_blocks(blocks),
        "line_counts": line_counts,
        "document_title_norm": _normalize_heading_line(str(metadata.get("title") or "")),
        "figure_page_stats": figure_page_stats,
        "figure_bboxes_by_page": figure_bboxes_by_page,
        "table_regions": table_regions,
        "table_pages": _table_pages(table_regions=table_regions, bundled_assets=bundled_assets),
    }


def _filter_bundled_assets_for_markdown(
    *,
    blocks: List[Dict[str, Any]],
    bundled_assets: Dict[str, Any],
) -> Dict[str, Any]:
    page_bounds = _page_bounds_for_blocks(blocks)
    filtered = dict(bundled_assets)

    figures = [item for item in bundled_assets.get("figures", []) if isinstance(item, dict)]
    figure_page_stats: Dict[int, Dict[str, int]] = defaultdict(lambda: {"embedded": 0, "vector_with_caption": 0})
    for figure in figures:
        page_no = _safe_int(figure.get("page_no"), 0)
        if page_no <= 0:
            continue
        if str(figure.get("figure_type") or "") == "embedded":
            figure_page_stats[page_no]["embedded"] += 1
        if str(figure.get("figure_type") or "") == "vector" and str(figure.get("figure_caption") or "").strip():
            figure_page_stats[page_no]["vector_with_caption"] += 1

    max_embedded_per_page = max(1, _safe_int(os.getenv("MARKDOWN_MAX_EMBEDDED_IMAGES_PER_PAGE", "8"), 8))
    min_large_embedded_area_ratio = min(1.0, max(0.0, _safe_float(os.getenv("MARKDOWN_MIN_LARGE_EMBEDDED_AREA_RATIO", "0.08"), 0.08)))

    kept_figures: List[Dict[str, Any]] = []
    for figure in figures:
        page_no = _safe_int(figure.get("page_no"), 0)
        stats = figure_page_stats.get(page_no, {"embedded": 0, "vector_with_caption": 0})
        figure_type = str(figure.get("figure_type") or "")
        caption = str(figure.get("figure_caption") or "").strip()
        figure_number = str(figure.get("figure_number") or "").strip()
        figure_body = str(figure.get("figure_body") or "").strip()
        if not (caption or figure_number or figure_body):
            if figure_type != "embedded":
                continue
            allow_captionless = os.getenv("MARKDOWN_INCLUDE_CAPTIONLESS_EMBEDDED_FIGURES", "").strip().lower() in {"1", "true", "yes"}
            if not allow_captionless:
                continue
        if figure_type == "embedded" and not caption:
            if stats.get("vector_with_caption", 0) > 0:
                continue
            if stats.get("embedded", 0) >= max_embedded_per_page:
                bbox = figure.get("bbox") if isinstance(figure.get("bbox"), dict) else {}
                page_box = page_bounds.get(page_no)
                if not page_box or _bbox_area_ratio(bbox, page_box) < min_large_embedded_area_ratio:
                    continue
        kept_figures.append(figure)
    filtered["figures"] = kept_figures

    filtered["tables"] = [
        item
        for item in bundled_assets.get("tables", [])
        if isinstance(item, dict) and _table_record_is_renderable(item)
    ]
    filtered["equations"] = [
        item
        for item in bundled_assets.get("equations", [])
        if isinstance(item, dict) and _equation_record_is_renderable(item)
    ]
    return filtered


def _bbox_area_ratio(bbox: Any, page_bounds: Optional[Tuple[float, float, float, float]]) -> float:
    if not isinstance(bbox, dict) or page_bounds is None:
        return 0.0
    page_area = max(1e-6, max(0.0, page_bounds[2] - page_bounds[0]) * max(0.0, page_bounds[3] - page_bounds[1]))
    return _rect_area(bbox) / page_area


def _table_record_is_renderable(record: Dict[str, Any]) -> bool:
    caption = str(record.get("caption") or "").strip()
    headers = record.get("headers") if isinstance(record.get("headers"), list) else []
    rows = record.get("rows") if isinstance(record.get("rows"), list) else []
    n_rows = _safe_int(record.get("n_rows"), len(rows))
    n_cols = _safe_int(record.get("n_cols"), len(headers) or (len(rows[0]) if rows and isinstance(rows[0], list) else 0))
    max_cell_len = 0
    prose_like_rows = 0
    numeric_rows = 0
    for row in rows:
        if isinstance(row, list):
            row_text = " ".join(str(cell or "").strip() for cell in row if str(cell or "").strip())
            if row_text:
                if _looks_like_sentenceish_prose(row_text):
                    prose_like_rows += 1
                if sum(1 for cell in row if re.search(r"\d", str(cell or ""))) >= max(1, len(row) // 3):
                    numeric_rows += 1
            for cell in row:
                max_cell_len = max(max_cell_len, len(str(cell or "").strip()))
    for cell in headers:
        max_cell_len = max(max_cell_len, len(str(cell or "").strip()))

    if n_rows <= 0:
        return bool(caption)
    if n_rows < 2:
        return False
    if n_cols < 2:
        return False
    if not caption and max_cell_len >= 120:
        return False
    normalized_caption = _normalize_caption_text(caption)
    if normalized_caption:
        row_joined = _normalize_caption_text(" ".join(" ".join(str(cell or "").strip() for cell in row if str(cell or "").strip()) for row in rows))
        caption_tokens = [token for token in normalized_caption.split() if len(token) >= 4]
        if row_joined and caption_tokens:
            token_hits = sum(1 for token in caption_tokens if token in row_joined)
            if token_hits >= max(2, len(caption_tokens) // 2):
                return False
    if prose_like_rows >= max(2, len(rows) // 2) and numeric_rows == 0:
        return False
    return True


def _equation_record_is_renderable(record: Dict[str, Any]) -> bool:
    text = str(record.get("text") or "").strip()
    latex = str(record.get("latex") or "").strip()
    candidate = text or latex
    if not candidate:
        return False

    lowered = candidate.lower()
    if candidate.lstrip().startswith(("⋆", "†", "*", "‡")):
        return False
    if any(marker in lowered for marker in ["http://", "https://", "www.", "github", "openreview", "arxiv", "project page", "code:", "url "]):
        return False
    if "equal contribution" in lowered:
        return False
    if any(marker in lowered for marker in [" at noise level", "following ", "reconstruction noise scale", "figure ", "table "]):
        return False
    if re.search(r"\.\s+[a-z]", lowered):
        return False

    lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    if len(lines) >= 3 and all(re.fullmatch(r"[A-Za-z]\s*=\s*\d+(?:\.\d+)?", line) for line in lines):
        return False

    word_count = len(re.findall(r"[A-Za-z]{2,}", candidate))
    math_token_count = len(re.findall(r"[=+\-*/^_<>∥∑∫\\()\[\]{}]", candidate))
    if word_count >= 10 and math_token_count < 6:
        return False
    for line in lines:
        alpha_words = re.findall(r"[A-Za-z]{2,}", line)
        line_math_tokens = len(re.findall(r"[=+\-*/^_<>∥∑∫\\()\[\]{}]", line))
        if len(alpha_words) >= 6 and line_math_tokens < 3:
            return False
        if line_math_tokens < 4 and re.search(r"\b(with|given|where|then|using|following|under|during)\b", line.lower()):
            return False

    return True


def _block_owned_by_asset(block: Dict[str, Any], asset: Dict[str, Any], *, caption_key: str) -> bool:
    block_page = _safe_int(block.get("page_no"), 0)
    asset_page = _safe_int(asset.get("page_no"), 0)
    if block_page <= 0 or asset_page <= 0 or block_page != asset_page:
        return False

    block_bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    asset_bbox = asset.get("bbox") if isinstance(asset.get("bbox"), dict) else {}
    if not block_bbox or not asset_bbox:
        return False

    overlap = _rect_overlap(block_bbox, asset_bbox)
    block_area = _rect_area(block_bbox)
    if block_area > 0 and overlap / block_area >= 0.45:
        return True
    if _point_in_bbox(_bbox_center(block_bbox), asset_bbox):
        return True
    expanded_bbox = _expand_bbox(
        asset_bbox,
        margin_x=90.0 if caption_key == "figure_caption" else 22.0,
        margin_y=24.0 if caption_key == "figure_caption" else 18.0,
    )
    block_text = str(block.get("text") or "").strip()
    if block_text and len(block_text) <= 48 and _point_in_bbox(_bbox_center(block_bbox), expanded_bbox):
        return True

    caption = str(asset.get(caption_key) or "").strip()
    if not caption:
        return False
    if not block_text:
        return False

    normalized_caption = _normalize_caption_text(caption)
    normalized_block = _normalize_caption_text(block_text)
    if not normalized_caption or not normalized_block:
        return False

    similar_caption = normalized_block.startswith(normalized_caption) or normalized_caption.startswith(normalized_block)
    if not similar_caption:
        return False

    block_y0 = _bbox_coord(block_bbox, "y0")
    block_y1 = _bbox_coord(block_bbox, "y1")
    asset_y0 = _bbox_coord(asset_bbox, "y0")
    asset_y1 = _bbox_coord(asset_bbox, "y1")
    vertical_gap = min(abs(block_y0 - asset_y1), abs(asset_y0 - block_y1))
    x_overlap = _x_overlap_ratio(block_bbox, asset_bbox)
    return vertical_gap <= 48.0 and x_overlap >= 0.2


def _vertical_gap(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> float:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return float("inf")
    return min(
        abs(_bbox_coord(a, "y0") - _bbox_coord(b, "y1")),
        abs(_bbox_coord(b, "y0") - _bbox_coord(a, "y1")),
    )


def _looks_like_front_matter_name_block(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    if not compact or "," in compact or "@" in compact or "http" in compact.lower():
        return False
    if _looks_like_table_caption(compact) or _parse_figure_caption(compact):
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'.-]*", compact)
    if len(tokens) < 2 or len(tokens) > 8:
        return False
    if any(token.lower() in {"the", "and", "for", "with", "from", "into", "using", "while"} for token in tokens):
        return False
    return all(token[:1].isupper() for token in tokens)


def _looks_like_front_matter_author_block(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    lowered = compact.lower()
    if not compact or "http" in lowered or "@" in compact:
        return False
    if _looks_like_table_caption(compact) or _parse_figure_caption(compact):
        return False
    if _looks_like_sentenceish_prose(compact):
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'.-]*", compact)
    if len(tokens) < 4 or len(tokens) > 28:
        return False
    capitalized = sum(1 for token in tokens if token[:1].isupper())
    if capitalized < max(4, len(tokens) // 2):
        return False
    if any(token.lower() in {"university", "institute", "laboratory", "department", "college", "project", "page"} for token in tokens):
        return False
    return any(marker in compact for marker in ["*", ",", " 1", " 2", " 3", " 4", " and "])


def _is_document_title_block(block: Dict[str, Any], *, text: str, render_state: Dict[str, Any]) -> bool:
    title_norm = str(render_state.get("document_title_norm") or "").strip()
    if not title_norm:
        return False
    page_no = _safe_int(block.get("page_no"), 0)
    if page_no <= 0 or page_no > 2:
        return False
    return _normalize_heading_line(text) == title_norm


def _is_front_matter_narrative_block(block: Dict[str, Any], *, text: str, render_state: Dict[str, Any]) -> bool:
    page_no = _safe_int(block.get("page_no"), 0)
    if page_no <= 0 or page_no > 2:
        return False
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return False
    bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    page_bounds = render_state.get("page_bounds", {}).get(page_no)
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    line_count = _safe_int(metadata.get("line_count"), max(1, len(str(text or "").splitlines())))
    char_count = _safe_int(metadata.get("char_count"), len(compact))
    max_font_size = _safe_float(metadata.get("max_font_size"), 0.0)
    section_canonical = str(metadata.get("section_canonical") or "")
    lowered = compact.lower()

    if any(
        marker in lowered
        for marker in [
            "equal contribution",
            "work done while",
            "project page",
            "code:",
            "website:",
            "demo:",
            "supplementary:",
            "correspondence to",
        ]
    ):
        return False
    if "http" in lowered or "github.com" in lowered or "@" in compact:
        return False

    y0_rel = 1.0
    if page_bounds and bbox:
        _, page_y0, _, page_y1 = page_bounds
        page_height = max(1e-6, page_y1 - page_y0)
        y0_rel = (_bbox_coord(bbox, "y0") - page_y0) / page_height

    if page_no == 1 and (_looks_like_front_matter_name_block(compact) or _looks_like_front_matter_author_block(compact)):
        return y0_rel <= 0.32

    if page_no == 1 and y0_rel <= 0.48:
        if re.search(r"\b(university|institute|laboratory|school|department|college|technologies|labs?)\b", lowered):
            return True

    if lowered.startswith("abstract") or lowered.startswith("keywords"):
        return True

    if section_canonical == "abstract" and y0_rel <= 0.72 and char_count >= 80:
        return True

    return False


def _matches_rendered_figure_caption_block(block: Dict[str, Any], figure: Dict[str, Any]) -> bool:
    block_page = _safe_int(block.get("page_no"), 0)
    figure_page = _safe_int(figure.get("page_no"), 0)
    if block_page <= 0 or figure_page <= 0 or block_page != figure_page:
        return False
    block_text = str(block.get("text") or "").strip()
    parsed_block = _parse_figure_caption(block_text)
    if not parsed_block:
        return False
    figure_number = _figure_display_number(figure)
    if not figure_number or figure_number != parsed_block["number"]:
        return False
    block_bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    figure_bbox = figure.get("bbox") if isinstance(figure.get("bbox"), dict) else {}
    if not block_bbox or not figure_bbox:
        return False
    return _x_overlap_ratio(block_bbox, figure_bbox) >= 0.25 and _vertical_gap(block_bbox, figure_bbox) <= 80.0


def _matches_rendered_table_caption_block(block: Dict[str, Any], table: Dict[str, Any]) -> bool:
    block_page = _safe_int(block.get("page_no"), 0)
    table_page = _safe_int(table.get("page_no"), 0)
    if block_page <= 0 or table_page <= 0 or block_page != table_page:
        return False
    block_text = str(block.get("text") or "").strip()
    if not _looks_like_table_caption(block_text):
        return False
    block_key = _table_caption_key(block_text)
    table_key = _table_caption_key(str(table.get("caption") or ""))
    if not block_key or not table_key or block_key != table_key:
        return False
    block_bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    table_bbox = table.get("bbox") if isinstance(table.get("bbox"), dict) else {}
    if not block_bbox or not table_bbox:
        return False
    return _x_overlap_ratio(block_bbox, table_bbox) >= 0.2 and _vertical_gap(block_bbox, table_bbox) <= 90.0


def _should_skip_block_text(block: Dict[str, Any], *, bundled_assets: Dict[str, Any], render_state: Dict[str, Any]) -> bool:
    text = str(block.get("text") or "").strip()
    if not text:
        return True
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    line_count = _safe_int(metadata.get("line_count"), max(1, len(text.splitlines())))
    char_count = _safe_int(metadata.get("char_count"), len(text))
    if _is_document_title_block(block, text=text, render_state=render_state):
        return True
    if _is_front_matter_narrative_block(block, text=text, render_state=render_state):
        return False
    if ("http://" in text or "https://" in text) and line_count <= 2 and char_count <= 180 and not _looks_like_sentenceish_prose(text):
        return True
    if _looks_like_visual_legend_text(text) and not _looks_like_front_matter_name_block(text):
        return True
    if _is_page_furniture_block(block, text=text, render_state=render_state):
        return True
    if _is_front_matter_metadata_block(block, text=text):
        return True
    if _is_figure_label_noise_block(block, text=text, render_state=render_state):
        return True
    if _is_inferred_table_region_block(block, text=text, render_state=render_state):
        return True
    if _is_table_scaffold_page_block(block, text=text, render_state=render_state):
        return True
    for figure in bundled_assets.get("figures", []):
        if isinstance(figure, dict) and _matches_rendered_figure_caption_block(block, figure):
            return True
        if isinstance(figure, dict) and _block_owned_by_asset(block, figure, caption_key="figure_caption"):
            return True
    for table in bundled_assets.get("tables", []):
        if isinstance(table, dict) and _matches_rendered_table_caption_block(block, table):
            return True
        if isinstance(table, dict) and _block_owned_by_asset(block, table, caption_key="caption"):
            return True
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    section_title = str(metadata.get("section_title") or "").strip()
    if not section_title:
        return False
    first_line = str((metadata.get("first_line") or (text.splitlines()[0] if text.splitlines() else text))).strip()
    normalized_title = _normalize_heading_line(section_title)
    normalized_line = _normalize_heading_line(first_line)
    if not normalized_title or not normalized_line:
        return False
    if normalized_line == normalized_title:
        return True
    if len(text) <= 220 and _looks_like_redundant_heading(first_line, normalized_title, normalized_line):
        return True
    return False


def _is_page_furniture_block(block: Dict[str, Any], *, text: str, render_state: Dict[str, Any]) -> bool:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    if str(metadata.get("layout_role") or "") == "margin_note":
        return True
    page_no = _safe_int(block.get("page_no"), 0)
    bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    page_bounds = render_state.get("page_bounds", {}).get(page_no)
    stripped = text.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    if "arxiv:" in lowered:
        return True
    if lowered in {"preprint", "preprint."}:
        return True
    if re.fullmatch(r"\d{1,3}", stripped):
        return True

    title_norm = str(render_state.get("document_title_norm") or "").strip()
    text_norm = _normalize_heading_line(stripped)
    line_counts: Counter[str] = render_state.get("line_counts", Counter())
    repeated_count = line_counts.get(_line_signature(stripped), 0)

    if title_norm and text_norm == title_norm and repeated_count >= 2:
        return True
    if repeated_count >= 4 and not stripped.startswith(("#", ">", "![", "|")):
        return True

    if page_bounds and bbox:
        _, page_y0, _, page_y1 = page_bounds
        page_height = max(1e-6, page_y1 - page_y0)
        y0_rel = (_bbox_coord(bbox, "y0") - page_y0) / page_height
        y1_rel = (_bbox_coord(bbox, "y1") - page_y0) / page_height
        if (
            page_no > 1
            and y0_rel <= 0.16
            and len(stripped.split()) <= 4
            and (
                ("et al" in lowered)
                or (repeated_count >= 2 and lowered in {"abstract", "introduction", "references", "appendix"})
            )
        ):
            return True
        if y0_rel <= 0.15 and repeated_count >= 2 and len(stripped.split()) <= 6:
            return True
        if (y0_rel <= 0.08 or y1_rel >= 0.93) and repeated_count >= 2:
            return True

    return False


def _is_front_matter_metadata_block(block: Dict[str, Any], *, text: str) -> bool:
    page_no = _safe_int(block.get("page_no"), 0)
    if page_no <= 0 or page_no > 2:
        return False
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    line_count = _safe_int(metadata.get("line_count"), max(1, len(str(text or "").splitlines())))
    char_count = _safe_int(metadata.get("char_count"), len(text))
    first_line = str(metadata.get("first_line") or text.splitlines()[0] if text.splitlines() else text).strip().lower()
    lowered = text.lower()
    if any(first_line.startswith(marker) for marker in ["code:", "project page", "supplementary:", "website:", "demo:", "correspondence to"]):
        return True
    if "corresponding author" in lowered:
        return True
    if "github.com" in lowered and line_count <= 3 and char_count <= 220:
        return True
    if "equal contribution" in lowered or "work done while" in lowered:
        return True
    if "@" in text and "." in text and line_count <= 3 and char_count <= 200:
        return True
    bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    if (
        page_no == 1
        and bbox
        and _bbox_coord(bbox, "y1") <= 210.0
        and line_count <= 3
        and char_count <= 120
        and "," in text
        and len(text.split()) <= 10
    ):
        return True
    if re.search(r"\b(university|institute|laboratory|school of|department of|college of|adobe|google|openai|meta|mit)\b", lowered):
        if char_count <= 180 and line_count <= 4 and (re.search(r"(^|\s)\d+(\s|$)", text) or "*" in text):
            return True
    return False


def _looks_like_visual_label_text(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return False
    if re.match(r"^\([a-z]\)\s+[A-Za-z]", compact, flags=re.IGNORECASE):
        return True
    if len(compact) > 48:
        return False
    if _looks_like_table_caption(compact):
        return False
    if _parse_figure_caption(compact):
        return False
    if re.search(r"[.!?]$", compact) and len(compact.split()) > 2:
        return False
    words = compact.split()
    if len(words) > 6:
        return False
    if any(ch.isdigit() for ch in compact) and len(words) > 3:
        return False
    stopwords = re.findall(r"\b(the|and|that|with|from|this|these|their|using|while|because)\b", compact.lower())
    if stopwords:
        return False
    return True


def _looks_like_visual_legend_text(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return False
    marker_count = len(re.findall(r"[■□●○▲△◆◇]", compact))
    if marker_count >= 2:
        return True
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    if any(len(line) > 36 or len(line.split()) > 4 for line in lines):
        return False
    if any(re.search(r"[.!?]$", line) for line in lines):
        return False
    return True


def _is_figure_label_noise_block(block: Dict[str, Any], *, text: str, render_state: Dict[str, Any]) -> bool:
    page_no = _safe_int(block.get("page_no"), 0)
    bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    if (
        page_no == 1
        and bbox
        and _bbox_coord(bbox, "y1") <= 190.0
        and _safe_int(metadata.get("line_count"), max(1, len(str(text or "").splitlines()))) <= 3
        and _looks_like_front_matter_name_block(text)
    ):
        return False
    looks_like_label = _looks_like_visual_label_text(text)
    looks_like_legend = _looks_like_visual_legend_text(text)
    if not (looks_like_label or looks_like_legend):
        return False
    if page_no <= 0:
        return False
    if not bbox:
        return False
    if str(metadata.get("layout_role") or "") == "full_width":
        return False
    figures = render_state.get("figure_bboxes_by_page", {}).get(page_no, [])
    if not figures:
        return False
    compact = " ".join(str(text or "").split()).strip()
    if re.match(r"^\([a-z]\)\s+[A-Za-z]", compact, flags=re.IGNORECASE):
        return True
    if looks_like_legend:
        return True

    expanded_margin_x = max(18.0, _safe_float(os.getenv("MARKDOWN_FIGURE_LABEL_MARGIN_X_PT", "40"), 40.0))
    expanded_margin_y = max(10.0, _safe_float(os.getenv("MARKDOWN_FIGURE_LABEL_MARGIN_Y_PT", "28"), 28.0))
    center = _bbox_center(bbox)
    for figure in figures:
        fig_bbox = figure.get("bbox") if isinstance(figure.get("bbox"), dict) else {}
        if not fig_bbox:
            continue
        figure_type = str(figure.get("figure_type") or "")
        caption = str(figure.get("caption") or "").strip()
        extra_margin_x = expanded_margin_x
        extra_margin_y = expanded_margin_y
        if figure_type == "embedded" and not caption:
            fig_width = max(0.0, _bbox_coord(fig_bbox, "x1") - _bbox_coord(fig_bbox, "x0"))
            fig_height = max(0.0, _bbox_coord(fig_bbox, "y1") - _bbox_coord(fig_bbox, "y0"))
            extra_margin_x = max(extra_margin_x, fig_width * 0.35)
            extra_margin_y = max(extra_margin_y, fig_height * 0.2)
        expanded = _expand_bbox(fig_bbox, margin_x=extra_margin_x, margin_y=extra_margin_y)
        if _point_in_bbox(center, expanded):
            return True
        if _rect_overlap(bbox, _expand_bbox(fig_bbox, margin_x=8.0, margin_y=8.0)) > 0:
            return True
    return False


def _is_inferred_table_region_block(block: Dict[str, Any], *, text: str, render_state: Dict[str, Any]) -> bool:
    if _looks_like_table_caption(text):
        return False
    page_no = _safe_int(block.get("page_no"), 0)
    bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
    if page_no <= 0 or not bbox:
        return False
    y0 = _bbox_coord(bbox, "y0")
    y1 = _bbox_coord(bbox, "y1")
    for region in render_state.get("table_regions", {}).get(page_no, []):
        if y0 >= region["y0"] - 6.0 and y1 <= region["y1"] + 6.0:
            return True
    return False


def _is_table_scaffold_page_block(block: Dict[str, Any], *, text: str, render_state: Dict[str, Any]) -> bool:
    page_no = _safe_int(block.get("page_no"), 0)
    if page_no <= 0:
        return False
    if page_no not in render_state.get("table_pages", set()):
        return False
    return _looks_like_table_scaffold_text(text)


def _normalize_heading_line(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^\d+(?:\.\d+)*[\)\.]?\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _normalize_caption_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^(figure|fig\.?|table|tab\.?)\s*\d+[a-z]?\s*:\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _looks_like_redundant_heading(first_line: str, normalized_title: str, normalized_line: str) -> bool:
    if not first_line or not normalized_title or not normalized_line:
        return False
    if first_line.rstrip().endswith("."):
        return False
    if normalized_line.startswith(normalized_title) or normalized_title.startswith(normalized_line):
        return True
    similarity = SequenceMatcher(None, normalized_line, normalized_title).ratio()
    if similarity >= 0.82 and (re.match(r"^\d+(?:\.\d+)*\.?\s+", first_line.strip()) or len(first_line.split()) <= 12):
        return True
    return False


def _looks_like_table_caption(text: str) -> bool:
    compact = " ".join(str(text or "").split())
    return bool(re.match(r"^Table\s+\d+[A-Za-z]?(?:[\.:]|\s)", compact))


def _looks_like_table_scaffold_text(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return False
    if _looks_like_table_caption(compact):
        return False
    if compact.startswith("Figure "):
        return False
    if len(compact) >= 220 and _looks_like_sentenceish_prose(compact):
        return False
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    lowered = compact.lower()
    short_tokens = sum(1 for token in re.findall(r"\S+", compact) if len(token) <= 4)
    numberish_tokens = sum(1 for token in re.findall(r"\S+", compact) if re.search(r"\d|[%↑↓×†⋆✓–—-]", token))
    metric_markers = len(re.findall(r"(FID|IS|rFID|gFID|RMSD|Match|Valid|Unique|Params|Aux\.?|Adv\.?|Token|Method)", compact))
    if metric_markers >= 2 and (numberish_tokens >= 2 or short_tokens >= 6):
        return True
    if not _looks_like_sentenceish_prose(compact) and numberish_tokens >= 3:
        return True
    if numberish_tokens >= 4 and short_tokens >= 6 and not _looks_like_sentenceish_prose(compact):
        return True
    if (
        len(compact) <= 160
        and not _looks_like_sentenceish_prose(compact)
        and re.search(r"\b(with|without|single-stage|two-stage|concurrent|frameworks?|tokenizer|encoder|ours|weights|decoder|baseline)\b", lowered)
        and (numberish_tokens >= 1 or short_tokens >= 4)
    ):
        return True
    if compact.startswith(("⋆", "†", "* ")) and len(compact) <= 120:
        return True
    if lines and len(lines) <= 2 and len(compact) <= 140 and re.search(r"(?:^|[^\w])(FID|IS|rFID|RMSD|Match|Valid|Unique|Params)(?:$|[^\w])", compact):
        return True
    return False


def _looks_like_sentenceish_prose(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"[.!?]\s", text):
        return True
    stopwords = re.findall(r"\b(the|and|that|with|from|this|these|our|their|which|while|using|without|into|through|because|however|although)\b", lowered)
    return len(stopwords) >= 3


def _looks_like_section_boundary_block(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return False
    if compact.startswith("Figure "):
        return True
    if _looks_like_table_caption(compact):
        return True
    return bool(re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z]", compact))


def _infer_table_regions(blocks: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, float]]]:
    by_page: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        if not isinstance(block, dict):
            continue
        page_no = _safe_int(block.get("page_no"), 0)
        bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
        text = str(block.get("text") or "").strip()
        if page_no <= 0 or not bbox or not text:
            continue
        by_page[page_no].append(block)

    regions: Dict[int, List[Dict[str, float]]] = defaultdict(list)
    for page_no, page_blocks in by_page.items():
        ordered = sorted(page_blocks, key=lambda item: (_bbox_coord(item.get("bbox"), "y0"), _bbox_coord(item.get("bbox"), "x0")))
        total = len(ordered)
        for idx, block in enumerate(ordered):
            text = " ".join(str(block.get("text") or "").split()).strip()
            if not _looks_like_table_caption(text):
                continue
            bbox = block.get("bbox") if isinstance(block.get("bbox"), dict) else {}
            region_y0 = _bbox_coord(bbox, "y0")
            region_y1 = _bbox_coord(bbox, "y1")
            prev_y1 = region_y1
            taken = 0
            for probe in range(idx + 1, total):
                next_block = ordered[probe]
                next_text = " ".join(str(next_block.get("text") or "").split()).strip()
                if not next_text:
                    continue
                next_bbox = next_block.get("bbox") if isinstance(next_block.get("bbox"), dict) else {}
                if not next_bbox:
                    continue
                next_y0 = _bbox_coord(next_bbox, "y0")
                next_y1 = _bbox_coord(next_bbox, "y1")
                if next_y0 - prev_y1 > 72.0:
                    break
                if next_y1 - region_y0 > 320.0:
                    break
                if _looks_like_table_caption(next_text):
                    region_y1 = max(region_y1, next_y1)
                    prev_y1 = next_y1
                    taken += 1
                    continue
                if _looks_like_section_boundary_block(next_text) and not _looks_like_table_scaffold_text(next_text):
                    break
                if _looks_like_sentenceish_prose(next_text) and len(next_text) >= 180:
                    break
                if _looks_like_table_scaffold_text(next_text):
                    region_y1 = max(region_y1, next_y1)
                    prev_y1 = next_y1
                    taken += 1
                    continue
                if len(next_text) <= 80 and not _looks_like_sentenceish_prose(next_text):
                    region_y1 = max(region_y1, next_y1)
                    prev_y1 = next_y1
                    taken += 1
                    continue
                break
            if taken > 0:
                regions[page_no].append({"y0": region_y0, "y1": region_y1})
    return regions


def _table_pages(*, table_regions: Dict[int, List[Dict[str, float]]], bundled_assets: Dict[str, Any]) -> set[int]:
    pages = set(table_regions.keys())
    for table in bundled_assets.get("tables", []):
        if not isinstance(table, dict):
            continue
        page_no = _safe_int(table.get("page_no"), 0)
        if page_no > 0:
            pages.add(page_no)
    return pages


def _rect_area(bbox: Dict[str, Any]) -> float:
    width = max(0.0, _bbox_coord(bbox, "x1") - _bbox_coord(bbox, "x0"))
    height = max(0.0, _bbox_coord(bbox, "y1") - _bbox_coord(bbox, "y0"))
    return width * height


def _rect_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ix0 = max(_bbox_coord(a, "x0"), _bbox_coord(b, "x0"))
    iy0 = max(_bbox_coord(a, "y0"), _bbox_coord(b, "y0"))
    ix1 = min(_bbox_coord(a, "x1"), _bbox_coord(b, "x1"))
    iy1 = min(_bbox_coord(a, "y1"), _bbox_coord(b, "y1"))
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def _bbox_center(bbox: Dict[str, Any]) -> tuple[float, float]:
    return (
        (_bbox_coord(bbox, "x0") + _bbox_coord(bbox, "x1")) * 0.5,
        (_bbox_coord(bbox, "y0") + _bbox_coord(bbox, "y1")) * 0.5,
    )


def _point_in_bbox(point: tuple[float, float], bbox: Dict[str, Any]) -> bool:
    x, y = point
    return _bbox_coord(bbox, "x0") <= x <= _bbox_coord(bbox, "x1") and _bbox_coord(bbox, "y0") <= y <= _bbox_coord(bbox, "y1")


def _x_overlap_ratio(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ix0 = max(_bbox_coord(a, "x0"), _bbox_coord(b, "x0"))
    ix1 = min(_bbox_coord(a, "x1"), _bbox_coord(b, "x1"))
    overlap = max(0.0, ix1 - ix0)
    base = max(1e-6, min(max(0.0, _bbox_coord(a, "x1") - _bbox_coord(a, "x0")), max(0.0, _bbox_coord(b, "x1") - _bbox_coord(b, "x0"))))
    return overlap / base


def _expand_bbox(bbox: Dict[str, Any], *, margin_x: float, margin_y: float) -> Dict[str, float]:
    return {
        "x0": _bbox_coord(bbox, "x0") - margin_x,
        "y0": _bbox_coord(bbox, "y0") - margin_y,
        "x1": _bbox_coord(bbox, "x1") + margin_x,
        "y1": _bbox_coord(bbox, "y1") + margin_y,
    }


def _realign_asset_sections(*, blocks: List[Dict[str, Any]], bundled_assets: Dict[str, Any]) -> None:
    section_runs = _build_page_section_runs(blocks)
    for kind in ("figures", "tables", "equations"):
        updated: List[Dict[str, Any]] = []
        for record in bundled_assets.get(kind, []):
            if not isinstance(record, dict):
                continue
            updated.append(_realign_asset_section_record(record, section_runs))
        bundled_assets[kind] = updated


def _build_page_section_runs(blocks: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    runs: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        if not isinstance(block, dict):
            continue
        page_no = _safe_int(block.get("page_no"), 0)
        if page_no <= 0:
            continue
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        canonical = str(metadata.get("section_canonical") or "other").strip() or "other"
        title = str(metadata.get("section_title") or "Document Body").strip() or "Document Body"
        level = _safe_int(metadata.get("section_level"), 2)
        index = _safe_int(metadata.get("section_index"), 0)
        y0 = _bbox_coord(block.get("bbox"), "y0")
        page_runs = runs[page_no]
        if page_runs and page_runs[-1]["section_index"] == index and page_runs[-1]["section_canonical"] == canonical:
            continue
        page_runs.append(
            {
                "section_index": index,
                "section_canonical": canonical,
                "section_title": title,
                "section_level": level,
                "start_y": y0,
            }
        )
    return runs


def _realign_asset_section_record(record: Dict[str, Any], section_runs: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Any]:
    page_no = _safe_int(record.get("page_no"), 0)
    runs = section_runs.get(page_no) or []
    if not runs:
        return record
    bbox = record.get("bbox") if isinstance(record.get("bbox"), dict) else {}
    y0 = _bbox_coord(bbox, "y0") if bbox else None
    chosen = _choose_section_run(runs, y0)
    if not chosen:
        return record
    updated = dict(record)
    updated["section_canonical"] = chosen["section_canonical"]
    updated["section_title"] = chosen["section_title"]
    updated["section_level"] = chosen["section_level"]
    updated["section_index"] = chosen["section_index"]
    return updated


def _choose_section_run(runs: List[Dict[str, Any]], y0: Optional[float]) -> Optional[Dict[str, Any]]:
    if not runs:
        return None
    if y0 is None:
        non_front = [run for run in runs if run.get("section_canonical") != "front_matter"]
        return non_front[0] if non_front else runs[0]
    preceding = [run for run in runs if _safe_float(run.get("start_y"), 0.0) <= y0 + 8.0]
    if preceding:
        return preceding[-1]
    return runs[0]


def _postprocess_rendered_markdown(markdown: str, *, metadata: Dict[str, Any]) -> str:
    title_norm = _normalize_heading_line(str(metadata.get("title") or ""))
    lines = markdown.splitlines()
    counts = Counter(_line_signature(line) for line in lines if _line_signature(line))
    cleaned: List[str] = []
    for line in lines:
        stripped = line.strip()
        signature = _line_signature(line)
        if not stripped:
            cleaned.append(line)
            continue
        if re.fullmatch(r"\d{1,3}", stripped):
            continue
        if stripped.lower().startswith("arxiv:"):
            continue
        if title_norm and _normalize_heading_line(stripped) == title_norm and counts.get(signature, 0) >= 2:
            continue
        if counts.get(signature, 0) >= 4 and not stripped.startswith(("#", ">", "![", "|", "---")):
            continue
        cleaned.append(line)

    output = "\n".join(cleaned).strip() + "\n"
    output = re.sub(r"\n{3,}", "\n\n", output)
    return output


def _resolve_bundle_dir(paper_id: int, output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        return Path(output_dir).expanduser().resolve()
    configured = os.getenv("MARKDOWN_OUTPUT_DIR", "").strip()
    root = Path(configured).expanduser().resolve() if configured else (Path.cwd() / ".ia_phase1_data" / "markdown").expanduser().resolve()
    return root / str(int(paper_id))


def _prepare_bundle_dir(bundle_dir: Path, *, overwrite: bool) -> None:
    if bundle_dir.exists() and overwrite:
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)


def _manifest_asset_view(item: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in keys:
        if key in item and item.get(key) is not None:
            payload[key] = item.get(key)
    return payload
