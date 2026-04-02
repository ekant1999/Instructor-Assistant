from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from markdown_evaluation.scripts._common import ROOT, gold_doc_path, read_json, select_docs, system_doc_dir


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def render_curation_index(doc_ids: List[str] | None = None) -> str:
    docs = select_docs(doc_ids)
    lines: List[str] = [
        "# Gold Curation Index",
        "",
        "Use this file to validate each pilot document against the source PDF and both markdown outputs.",
        "",
    ]

    for doc in docs:
        ia_dir = system_doc_dir("ia_phase1", doc.doc_id)
        ocr_dir = system_doc_dir("ocr_agent", doc.doc_id)
        gold_path = gold_doc_path(doc.doc_id)
        ia_result = read_json(ia_dir / "benchmark_result.json", default={}) or {}
        ocr_result = read_json(ocr_dir / "benchmark_result.json", default={}) or {}
        validated = bool((read_json(gold_path, default={}) or {}).get("validated") is True)

        lines.extend(
            [
                f"## {doc.doc_id}: {doc.title}",
                "",
                f"- Gold validated: `{validated}`",
                f"- Layout: `{doc.layout_type}`",
                f"- Tags: `{', '.join(doc.doc_tags)}`",
                f"- PDF: `{_repo_rel(doc.pdf_path)}`",
                f"- Gold template: `{_repo_rel(gold_path)}`",
                f"- ia_phase1 markdown: `{_repo_rel(ia_dir / 'paper.md')}`",
                f"- ia_phase1 status/runtime: `{ia_result.get('status', 'missing')}` / `{float(ia_result.get('elapsed_ms') or 0.0):.1f} ms`",
                f"- ocr_agent markdown: `{_repo_rel(ocr_dir / 'paper.md')}`",
                f"- ocr_agent status/runtime: `{ocr_result.get('status', 'missing')}` / `{float(ocr_result.get('elapsed_ms') or 0.0):.1f} ms`",
                "- Validation checklist:",
                "  - headings and levels",
                "  - major section ordering",
                "  - 2-3 anchor snippets per major section",
                "  - figure numbers and captions",
                "  - table numbers and captions",
                "  - obvious markdown corruption notes",
                "",
            ]
        )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a markdown index for manual gold curation.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument(
        "--output",
        default="markdown_evaluation/reports/gold_curation.md",
        help="Output markdown path.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_curation_index(args.doc_ids), encoding="utf-8")
    print(f"[curation] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
