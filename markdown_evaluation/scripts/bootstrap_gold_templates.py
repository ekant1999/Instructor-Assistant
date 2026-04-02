from __future__ import annotations

import argparse
from typing import Any, Dict, List, Sequence

from markdown_evaluation.scripts._common import (
    BenchmarkDoc,
    gold_doc_path,
    normalize_match_text,
    normalized_doc_path,
    read_json,
    select_docs,
    write_json,
)


SYSTEM_PREFERENCE = ("ia_phase1", "ocr_agent")


def _candidate_headings(doc: BenchmarkDoc) -> List[Dict[str, Any]]:
    for system in SYSTEM_PREFERENCE:
        normalized = read_json(normalized_doc_path(system, doc.doc_id), default=None)
        if not normalized:
            continue
        headings = []
        for item in normalized.get("headings") or []:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            headings.append({"level": int(item.get("level") or 2), "text": text})
        if headings:
            return headings
    return []


def _candidate_assets(doc: BenchmarkDoc, kind: str) -> List[Dict[str, Any]]:
    for system in SYSTEM_PREFERENCE:
        normalized = read_json(normalized_doc_path(system, doc.doc_id), default=None)
        if not normalized:
            continue
        seen = set()
        items: List[Dict[str, Any]] = []
        for item in normalized.get(f"{kind}s") or []:
            number = item.get("number")
            if number is None or number in seen:
                continue
            seen.add(number)
            caption = str(item.get("caption") or "").strip()
            caption_tokens = [token for token in normalize_match_text(caption).split()[:8] if token]
            items.append({"number": int(number), "caption_contains": caption_tokens})
        if items:
            return items
    return []


def bootstrap_gold_templates(docs: Sequence[BenchmarkDoc], *, overwrite: bool = False) -> List[str]:
    paths: List[str] = []
    for doc in docs:
        path = gold_doc_path(doc.doc_id)
        if path.exists() and not overwrite:
            paths.append(str(path))
            continue
        payload = {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "validated": False,
            "layout_type": doc.layout_type,
            "doc_tags": list(doc.doc_tags),
            "headings": _candidate_headings(doc),
            "section_anchors": [],
            "figures": _candidate_assets(doc, "figure"),
            "tables": _candidate_assets(doc, "table"),
            "notes": doc.notes,
        }
        write_json(path, payload)
        paths.append(str(path))
    return paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap gold templates from normalized benchmark outputs.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument("--overwrite", action="store_true", default=False)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)
    paths = bootstrap_gold_templates(docs, overwrite=bool(args.overwrite))
    print(f"[gold] prepared {len(paths)} gold template(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
