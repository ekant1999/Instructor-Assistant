from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from markdown_evaluation.scripts._common import (
    BenchmarkDoc,
    collapse_ws,
    ensure_dirs,
    normalize_heading_text,
    normalize_match_text,
    normalized_doc_path,
    read_json,
    select_docs,
    system_doc_dir,
    write_json,
)

SYSTEMS = ("ia_phase1", "ocr_agent", "improved_ocr_agent", "improved_ocr_agent_marker")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)
_FIGURE_LINE_RE = re.compile(r"^\s*(?:[_>*`-]+\s*)?(?:figure|fig)\.?\s+(\d+|[IVXLCDM]{1,8})\b[:.]?\s*(.*)$", re.I)
_TABLE_LINE_RE = re.compile(r"^\s*(?:[_>*`-]+\s*)?table\s+(\d+|[IVXLCDM]{1,8})\b[:.]?\s*(.*)$", re.I)
_IMAGE_LINK_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]*)\)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_SUSPICIOUS_HEADING_RE = re.compile(r"^(?:\d+(?:[.]\d+)*|[A-Z]|[ivxlcdm]+|[\W_]+)$", re.I)
_PAGE_MODE_RE = re.compile(r"^\s*<!--\s*page\s+\d+\s+mode:", re.I)
_ASSET_LINE_RE = re.compile(r"^\s*(?:!\[.*\]\(.*\)|>\s*(?:Table|Equation)\s+JSON:|\[OCR unavailable.*\])")


def _strip_frontmatter(markdown: str) -> str:
    return _FRONTMATTER_RE.sub("", markdown, count=1).lstrip()


def _clean_heading_text(text: str) -> str:
    text = collapse_ws(text)
    text = text.rstrip("# ").strip()
    text = re.sub(r"^[*_`]+|[*_`]+$", "", text)
    return collapse_ws(text)


def _normalize_heading_for_match(text: str) -> str:
    return normalize_heading_text(_clean_heading_text(text))


def _strip_inline_markup(line: str) -> str:
    line = _HTML_COMMENT_RE.sub("", line)
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", line)
    line = re.sub(r"\[[^\]]+\]\([^)]*\)", " ", line)
    line = re.sub(r"[*_`>#]", " ", line)
    return collapse_ws(line)


def _line_has_meaningful_prose(line: str) -> bool:
    raw = line.strip()
    if not raw:
        return False
    if raw == "---":
        return False
    if _PAGE_MODE_RE.match(raw):
        return False
    if raw.startswith("<!--") and raw.endswith("-->"):
        return False
    if _ASSET_LINE_RE.match(raw):
        return False
    cleaned = _strip_inline_markup(raw)
    if not cleaned:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z0-9'\-]+", cleaned)
    return len(words) >= 3 or len(cleaned) >= 30


def _parse_caption_number(raw_value: str) -> Optional[int]:
    value = collapse_ws(raw_value).upper()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    if not re.fullmatch(r"[IVXLCDM]{1,8}", value):
        return None
    total = 0
    prev = 0
    roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    for char in reversed(value):
        current = roman_values[char]
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    return total if total > 0 else None


def _extract_title(markdown: str, fallback: str) -> str:
    for line in _strip_frontmatter(markdown).splitlines():
        match = _HEADING_RE.match(line.strip())
        if match and len(match.group(1)) == 1:
            return _clean_heading_text(match.group(2))
    return fallback


def _extract_headings(lines: Sequence[str]) -> List[Dict[str, Any]]:
    headings: List[Dict[str, Any]] = []
    for line_no, line in enumerate(lines, start=1):
        match = _HEADING_RE.match(line.strip())
        if not match:
            continue
        text = _clean_heading_text(match.group(2))
        if not text:
            continue
        headings.append(
            {
                "level": len(match.group(1)),
                "text": text,
                "normalized_text": _normalize_heading_for_match(text),
                "line_no": line_no,
                "suspicious": bool(_SUSPICIOUS_HEADING_RE.match(text)),
            }
        )
    return headings


def _build_sections(lines: Sequence[str], headings: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    sections: List[Dict[str, Any]] = []
    empty_count = 0
    consecutive_runs = 0
    max_run_length = 0
    current_run = 1

    for idx, heading in enumerate(headings):
        start_line = heading["line_no"] + 1
        end_line = headings[idx + 1]["line_no"] - 1 if idx + 1 < len(headings) else len(lines)
        segment_lines = list(lines[start_line - 1 : end_line])
        prose_lines = [line for line in segment_lines if _line_has_meaningful_prose(line)]
        prose_text = "\n".join(prose_lines).strip()
        full_text = "\n".join(line for line in segment_lines if line.strip()).strip()
        word_count = len(re.findall(r"[A-Za-z][A-Za-z0-9'\-]+", prose_text))
        asset_only = not prose_lines and any(_ASSET_LINE_RE.match(line.strip()) for line in segment_lines if line.strip())
        if word_count == 0:
            empty_count += 1

        sections.append(
            {
                "heading_text": heading["text"],
                "normalized_heading_text": heading["normalized_text"],
                "level": heading["level"],
                "line_start": heading["line_no"],
                "line_end": end_line,
                "prose_text": prose_text,
                "full_text": full_text,
                "word_count": word_count,
                "empty": word_count == 0,
                "asset_only": asset_only,
            }
        )

        if idx + 1 < len(headings):
            gap_lines = lines[heading["line_no"] : headings[idx + 1]["line_no"] - 1]
            has_prose = any(_line_has_meaningful_prose(line) for line in gap_lines)
            if has_prose:
                if current_run > 1:
                    consecutive_runs += 1
                    max_run_length = max(max_run_length, current_run)
                current_run = 1
            else:
                current_run += 1

    if current_run > 1:
        consecutive_runs += 1
        max_run_length = max(max_run_length, current_run)

    return sections, {
        "empty_section_count": empty_count,
        "consecutive_heading_run_count": consecutive_runs,
        "max_consecutive_heading_run": max_run_length,
    }


def _extract_numbered_captions(lines: Sequence[str], pattern: re.Pattern[str], kind: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for line_no, raw_line in enumerate(lines, start=1):
        candidates = [_strip_inline_markup(raw_line)]
        if not candidates[0]:
            for match_obj in _IMAGE_LINK_RE.finditer(raw_line):
                alt_text = collapse_ws(match_obj.group("alt"))
                if not alt_text:
                    continue
                alt_lower = alt_text.lower()
                if " on page " in alt_lower or len(alt_text.split()) >= 3 or alt_lower.startswith(("figure ", "fig ", "table ")):
                    candidates.append(alt_text)

        match = None
        cleaned = ""
        for candidate in candidates:
            candidate_match = pattern.match(candidate)
            if candidate_match:
                match = candidate_match
                cleaned = candidate
                break
        if not match:
            continue
        number = _parse_caption_number(match.group(1))
        if number is None:
            continue
        caption = collapse_ws(match.group(2))
        items.append({
            "number": number,
            "caption": caption,
            "normalized_caption": normalize_match_text(caption),
            "line_no": line_no,
            "kind": kind,
        })
    return items


def _count_duplicates(values: Sequence[str]) -> int:
    seen = set()
    duplicates = 0
    for value in values:
        if value in seen:
            duplicates += 1
        else:
            seen.add(value)
    return duplicates


def normalize_markdown_document(*, markdown: str, doc_id: str, system: str, source_pdf: str = "", title_hint: str = "", run_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    stripped = _strip_frontmatter(markdown)
    lines = stripped.splitlines()
    headings = _extract_headings(lines)
    sections, section_metrics = _build_sections(lines, headings)
    figures = _extract_numbered_captions(lines, _FIGURE_LINE_RE, "figure")
    tables = _extract_numbered_captions(lines, _TABLE_LINE_RE, "table")
    heading_norms = [heading["normalized_text"] for heading in headings]
    figure_norms = [str(item["number"]) for item in figures]
    table_norms = [str(item["number"]) for item in tables]

    intrinsic_metrics = {
        "heading_count": len(headings),
        "duplicate_heading_count": _count_duplicates(heading_norms),
        "suspicious_heading_count": sum(1 for heading in headings if heading["suspicious"]),
        "figure_caption_count": len(figures),
        "table_caption_count": len(tables),
        "duplicate_figure_caption_count": _count_duplicates(figure_norms),
        "duplicate_table_caption_count": _count_duplicates(table_norms),
        **section_metrics,
    }

    return {
        "doc_id": doc_id,
        "system": system,
        "source_pdf": source_pdf,
        "title": _extract_title(markdown, fallback=title_hint or doc_id),
        "status": str((run_metadata or {}).get("status") or "success"),
        "markdown_line_count": len(lines),
        "headings": headings,
        "sections": sections,
        "figures": figures,
        "tables": tables,
        "intrinsic_metrics": intrinsic_metrics,
        "run_metadata": run_metadata or {},
    }


def _load_system_markdown(system: str, doc: BenchmarkDoc) -> Tuple[str, Dict[str, Any], Path]:
    doc_dir = system_doc_dir(system, doc.doc_id)
    run_metadata = read_json(doc_dir / "benchmark_result.json", default={}) or {}
    if system == "ia_phase1":
        markdown_path = doc_dir / "paper.md"
    else:
        markdown_path = doc_dir / "paper.md"
    if not markdown_path.exists():
        if run_metadata:
            return "", run_metadata, markdown_path
        raise FileNotFoundError(f"Markdown output missing for {system}/{doc.doc_id}: {markdown_path}")
    return markdown_path.read_text(encoding="utf-8"), run_metadata, markdown_path


def normalize_system_outputs(docs: Sequence[BenchmarkDoc], *, systems: Sequence[str] = SYSTEMS) -> List[Dict[str, Any]]:
    ensure_dirs()
    rows: List[Dict[str, Any]] = []
    for system in systems:
        for doc in docs:
            markdown, run_metadata, markdown_path = _load_system_markdown(system, doc)
            normalized = normalize_markdown_document(
                markdown=markdown,
                doc_id=doc.doc_id,
                system=system,
                source_pdf=str(doc.pdf_path),
                title_hint=doc.title,
                run_metadata={**run_metadata, "markdown_path": str(markdown_path)},
            )
            write_json(normalized_doc_path(system, doc.doc_id), normalized)
            rows.append(normalized)
    return rows


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize benchmark markdown outputs into a common schema.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument("--systems", nargs="*", default=list(SYSTEMS), choices=list(SYSTEMS))
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)
    rows = normalize_system_outputs(docs, systems=args.systems)
    print(f"[normalize] wrote {len(rows)} normalized document(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
