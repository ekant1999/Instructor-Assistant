from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from _common import METADATA_PATH, REVIEW_DIR, ensure_dirs, read_jsonl


_ABSTRACT_RE = re.compile(
    r"\babstract\b[:\s]*(.+?)(?=\n\s*(?:1[\.\s]|introduction\b|keywords\b|index terms\b))",
    re.IGNORECASE | re.DOTALL,
)


def _clean_text(text: str) -> str:
    return " ".join((text or "").replace("\x00", " ").split())


def _extract_abstract_from_pages(pages: List[tuple[int, str]]) -> str:
    joined = "\n".join(text for _, text in pages[:2])
    match = _ABSTRACT_RE.search(joined)
    if match:
        return _clean_text(match.group(1))
    return _clean_text(joined[:2000])


def _render_review(record: Dict[str, Any], abstract: str, section_report: Dict[str, Any]) -> str:
    lines = [
        f"# {record['title']}",
        "",
        f"- paper_id: `{record['paper_id']}`",
        f"- arxiv_id: `{record['arxiv_id']}`",
        f"- benchmark_category: `{record['benchmark_category']}`",
        f"- primary_category: `{record['primary_category']}`",
        f"- published: `{record['published']}`",
        "",
        "## Abstract",
        "",
        abstract,
        "",
        "## Section Headings",
        "",
    ]
    for section in section_report.get("sections") or []:
        title = section.get("title") or section.get("canonical") or "untitled"
        lines.append(
            f"- `{section.get('canonical')}`: {title} (pages {section.get('start_page')}-{section.get('end_page')})"
        )
    lines.extend(
        [
            "",
            "## Search Notes",
            "",
            f"- Summary: {record['summary']}",
            "- Use this file to curate exact topical queries, paraphrases, and expected pages/sections.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    from backend.core.pdf import extract_pages
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path

    ensure_ia_phase1_on_path()

    from ia_phase1.parser import extract_text_blocks
    from ia_phase1.sectioning import annotate_blocks_with_sections

    ensure_dirs()
    metadata = read_jsonl(METADATA_PATH)
    if not metadata:
        raise RuntimeError("No metadata found. Run fetch_arxiv_papers.py first.")

    review_index: List[str] = ["# Benchmark Paper Reviews", ""]
    for record in metadata:
        pdf_path = Path(str(record["pdf_path"])).expanduser().resolve()
        pages = list(extract_pages(pdf_path))
        abstract = _extract_abstract_from_pages(pages)
        blocks = extract_text_blocks(pdf_path)
        section_report = annotate_blocks_with_sections(
            blocks,
            pdf_path,
            source_url=f"https://arxiv.org/abs/{record['arxiv_id']}",
        )
        review_text = _render_review(record, abstract, section_report)
        review_path = REVIEW_DIR / f"{record['paper_id']}_{record['arxiv_id']}.md"
        review_path.write_text(review_text, encoding="utf-8")
        review_index.append(f"- `{review_path.relative_to(REVIEW_DIR.parent)}`")

    (REVIEW_DIR / "INDEX.md").write_text("\n".join(review_index) + "\n", encoding="utf-8")
    print(json.dumps({"reviews": len(metadata), "review_dir": str(REVIEW_DIR)}, indent=2))


if __name__ == "__main__":
    main()
