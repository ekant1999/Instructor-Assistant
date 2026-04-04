from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from markdown_evaluation.scripts._common import (
    BenchmarkDoc,
    REPORT_DIR,
    RUN_DIR,
    ensure_dirs,
    heading_match_variants,
    load_gold_doc,
    normalize_heading_text,
    normalize_match_text,
    normalized_doc_path,
    read_json,
    select_docs,
    write_json,
)

SYSTEMS = ("ia_phase1", "ocr_agent", "improved_ocr_agent")


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _optional_recall(matched_count: int, gold_count: int) -> Optional[float]:
    if gold_count <= 0:
        return None
    return matched_count / gold_count


def _f1(precision: float, recall: float) -> float:
    if precision <= 0 or recall <= 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _heading_values_match(left: Any, right: Any) -> bool:
    left_values = left if isinstance(left, (set, list, tuple)) else [left]
    right_values = right if isinstance(right, (set, list, tuple)) else [right]
    return bool(set(str(item) for item in left_values if item) & set(str(item) for item in right_values if item))


def _lcs_length(left: Sequence[Any], right: Sequence[Any]) -> int:
    if not left or not right:
        return 0
    dp = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i, lhs in enumerate(left, start=1):
        for j, rhs in enumerate(right, start=1):
            if _heading_values_match(lhs, rhs):
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def _multiset_overlap(left: Iterable[str], right: Iterable[str]) -> int:
    left_counter = Counter(left)
    right_counter = Counter(right)
    overlap = left_counter & right_counter
    return sum(int(value) for value in overlap.values())


def _multiset_variant_overlap(left: Sequence[Sequence[str]], right: Sequence[Sequence[str]]) -> int:
    if not left or not right:
        return 0

    right_matches = [-1] * len(right)

    def _dfs(left_index: int, seen: set[int]) -> bool:
        for right_index, right_values in enumerate(right):
            if right_index in seen:
                continue
            if not _heading_values_match(left[left_index], right_values):
                continue
            seen.add(right_index)
            if right_matches[right_index] == -1 or _dfs(right_matches[right_index], seen):
                right_matches[right_index] = left_index
                return True
        return False

    matched = 0
    for left_index in range(len(left)):
        if _dfs(left_index, set()):
            matched += 1
    return matched


def _score_heading_metrics(normalized: Dict[str, Any], gold: Dict[str, Any]) -> Dict[str, Any]:
    gold_headings = [heading_match_variants(item.get("text") or "") for item in gold.get("headings") or []]
    gold_headings = [item for item in gold_headings if item]
    pred_headings = [
        heading_match_variants(item.get("text") or item.get("normalized_text") or "")
        for item in normalized.get("headings") or []
    ]
    pred_headings = [item for item in pred_headings if item]

    matched = _multiset_variant_overlap(pred_headings, gold_headings)
    precision = _safe_div(matched, len(pred_headings))
    recall = _safe_div(matched, len(gold_headings))
    order_score = _safe_div(_lcs_length(pred_headings, gold_headings), len(gold_headings))

    return {
        "heading_precision": precision,
        "heading_recall": recall,
        "heading_f1": _f1(precision, recall),
        "heading_order_score": order_score,
        "gold_heading_count": len(gold_headings),
        "pred_heading_count": len(pred_headings),
    }


def _score_anchor_metrics(normalized: Dict[str, Any], gold: Dict[str, Any]) -> Dict[str, Any]:
    anchors = gold.get("section_anchors") or []
    if not anchors:
        return {
            "anchor_count": 0,
            "anchor_recall": 0.0,
            "anchor_assignment_accuracy": 0.0,
            "anchor_wrong_section_count": 0,
            "anchor_miss_count": 0,
        }

    found = 0
    correct = 0
    wrong_section = 0
    misses = 0
    sections = normalized.get("sections") or []

    for anchor in anchors:
        needle = normalize_match_text(anchor.get("text") or "")
        expected_variants = heading_match_variants(anchor.get("expected_section") or "")
        if not needle or not expected_variants:
            continue
        matches = []
        for section in sections:
            haystack = normalize_match_text(section.get("prose_text") or section.get("full_text") or "")
            if needle and needle in haystack:
                matches.append(section)
        if not matches:
            misses += 1
            continue
        found += 1
        if any(
            _heading_values_match(heading_match_variants(section.get("heading_text") or ""), expected_variants)
            for section in matches
        ):
            correct += 1
        else:
            wrong_section += 1

    total = len([
        anchor
        for anchor in anchors
        if normalize_match_text(anchor.get("text") or "") and heading_match_variants(anchor.get("expected_section") or "")
    ])
    return {
        "anchor_count": total,
        "anchor_recall": _safe_div(found, total),
        "anchor_assignment_accuracy": _safe_div(correct, total),
        "anchor_wrong_section_count": wrong_section,
        "anchor_miss_count": misses,
    }


def _score_asset_metrics(normalized: Dict[str, Any], gold: Dict[str, Any]) -> Dict[str, Any]:
    pred_figure_numbers = {int(item.get("number")) for item in normalized.get("figures") or [] if item.get("number") is not None}
    pred_table_numbers = {int(item.get("number")) for item in normalized.get("tables") or [] if item.get("number") is not None}
    gold_figure_numbers = {int(item.get("number")) for item in gold.get("figures") or [] if item.get("number") is not None}
    gold_table_numbers = {int(item.get("number")) for item in gold.get("tables") or [] if item.get("number") is not None}

    return {
        "figure_recall": _optional_recall(len(pred_figure_numbers & gold_figure_numbers), len(gold_figure_numbers)),
        "table_recall": _optional_recall(len(pred_table_numbers & gold_table_numbers), len(gold_table_numbers)),
        "gold_figure_count": len(gold_figure_numbers),
        "gold_table_count": len(gold_table_numbers),
    }


def score_normalized_doc(normalized: Dict[str, Any], gold: Optional[Dict[str, Any]], doc: BenchmarkDoc) -> Dict[str, Any]:
    gold_validated = bool(gold and gold.get("validated") is True)
    intrinsic = dict(normalized.get("intrinsic_metrics") or {})
    elapsed_ms = float((normalized.get("run_metadata") or {}).get("elapsed_ms") or 0.0)

    payload: Dict[str, Any] = {
        "doc_id": doc.doc_id,
        "system": normalized.get("system"),
        "title": normalized.get("title") or doc.title,
        "layout_type": doc.layout_type,
        "doc_tags": list(doc.doc_tags),
        "status": normalized.get("status") or (normalized.get("run_metadata") or {}).get("status") or "success",
        "gold_available": gold_validated,
        "elapsed_ms": elapsed_ms,
        "intrinsic_metrics": intrinsic,
    }
    run_metadata = normalized.get("run_metadata") or {}
    if run_metadata.get("error_type"):
        payload["error_type"] = run_metadata.get("error_type")
    if run_metadata.get("error_message"):
        payload["error_message"] = run_metadata.get("error_message")
    if not gold_validated:
        return payload

    assert gold is not None
    payload.update(_score_heading_metrics(normalized, gold))
    payload.update(_score_anchor_metrics(normalized, gold))
    payload.update(_score_asset_metrics(normalized, gold))
    return payload


def _mean(values: Iterable[float]) -> float:
    values = [float(value) for value in values if value is not None]
    return sum(values) / len(values) if values else 0.0


def _format_optional_metric(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def _aggregate_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_system: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_system[str(row.get("system") or "unknown")].append(row)

    summary: Dict[str, Any] = {"systems": {}, "category_breakdown": {}}
    gold_metric_keys = [
        "heading_precision",
        "heading_recall",
        "heading_f1",
        "heading_order_score",
        "anchor_recall",
        "anchor_assignment_accuracy",
        "figure_recall",
        "table_recall",
    ]
    intrinsic_keys = [
        "duplicate_heading_count",
        "suspicious_heading_count",
        "empty_section_count",
        "consecutive_heading_run_count",
        "duplicate_figure_caption_count",
        "duplicate_table_caption_count",
    ]

    for system, system_rows in by_system.items():
        gold_rows = [row for row in system_rows if row.get("gold_available")]
        success_rows = [row for row in system_rows if row.get("status") == "success"]
        aggregate = {
            "document_count": len(system_rows),
            "gold_document_count": len(gold_rows),
            "success_count": len(success_rows),
            "failure_count": len(system_rows) - len(success_rows),
            "metrics": {key: _mean(row.get(key, 0.0) for row in gold_rows) for key in gold_metric_keys},
            "operational": {
                "elapsed_ms": _mean(row.get("elapsed_ms", 0.0) for row in system_rows),
            },
            "intrinsic": {key: _mean((row.get("intrinsic_metrics") or {}).get(key, 0.0) for row in system_rows) for key in intrinsic_keys},
        }
        summary["systems"][system] = aggregate

    all_tags = sorted({tag for row in rows for tag in row.get("doc_tags") or []})
    for tag in all_tags:
        summary["category_breakdown"][tag] = {}
        for system, system_rows in by_system.items():
            tagged = [row for row in system_rows if tag in (row.get("doc_tags") or [])]
            gold_tagged = [row for row in tagged if row.get("gold_available")]
            summary["category_breakdown"][tag][system] = {
                "document_count": len(tagged),
                "heading_f1": _mean(row.get("heading_f1", 0.0) for row in gold_tagged),
                "anchor_assignment_accuracy": _mean(row.get("anchor_assignment_accuracy", 0.0) for row in gold_tagged),
                "elapsed_ms": _mean(row.get("elapsed_ms", 0.0) for row in tagged),
                "duplicate_heading_count": _mean((row.get("intrinsic_metrics") or {}).get("duplicate_heading_count", 0.0) for row in tagged),
                "empty_section_count": _mean((row.get("intrinsic_metrics") or {}).get("empty_section_count", 0.0) for row in tagged),
            }
    return summary


def _render_markdown_report(rows: Sequence[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    lines: List[str] = ["# Markdown Benchmark Report", ""]
    lines.append("## Systems")
    lines.append("")
    for system, payload in (summary.get("systems") or {}).items():
        lines.append(f"### {system}")
        lines.append("")
        lines.append(f"- Documents: `{payload.get('document_count', 0)}`")
        lines.append(f"- Gold-scored documents: `{payload.get('gold_document_count', 0)}`")
        lines.append(f"- Successes: `{payload.get('success_count', 0)}`")
        lines.append(f"- Failures: `{payload.get('failure_count', 0)}`")
        metrics = payload.get("metrics") or {}
        operational = payload.get("operational") or {}
        intrinsic = payload.get("intrinsic") or {}
        lines.append(f"- Mean heading F1: `{metrics.get('heading_f1', 0.0):.3f}`")
        lines.append(f"- Mean anchor assignment accuracy: `{metrics.get('anchor_assignment_accuracy', 0.0):.3f}`")
        lines.append(f"- Mean figure recall: `{metrics.get('figure_recall', 0.0):.3f}`")
        lines.append(f"- Mean table recall: `{metrics.get('table_recall', 0.0):.3f}`")
        lines.append(f"- Mean runtime (ms): `{operational.get('elapsed_ms', 0.0):.1f}`")
        lines.append(f"- Mean duplicate heading count: `{intrinsic.get('duplicate_heading_count', 0.0):.2f}`")
        lines.append(f"- Mean empty section count: `{intrinsic.get('empty_section_count', 0.0):.2f}`")
        lines.append("")

    lines.append("## Per-Document Scores")
    lines.append("")
    for row in sorted(rows, key=lambda item: (item.get("doc_id", ""), item.get("system", ""))):
        lines.append(f"### {row.get('doc_id')} / {row.get('system')}")
        lines.append("")
        lines.append(f"- Title: `{row.get('title', '')}`")
        lines.append(f"- Layout: `{row.get('layout_type', 'unknown')}`")
        lines.append(f"- Tags: `{', '.join(row.get('doc_tags') or [])}`")
        lines.append(f"- Status: `{row.get('status', 'unknown')}`")
        lines.append(f"- Runtime (ms): `{float(row.get('elapsed_ms', 0.0)):.1f}`")
        if row.get("error_type"):
            lines.append(f"- Error: `{row.get('error_type')}: {row.get('error_message', '')}`")
        if row.get("gold_available"):
            lines.append(f"- Heading F1: `{_format_optional_metric(row.get('heading_f1'))}`")
            lines.append(f"- Heading order score: `{_format_optional_metric(row.get('heading_order_score'))}`")
            lines.append(f"- Anchor recall: `{_format_optional_metric(row.get('anchor_recall'))}`")
            lines.append(f"- Anchor assignment accuracy: `{_format_optional_metric(row.get('anchor_assignment_accuracy'))}`")
            lines.append(f"- Figure recall: `{_format_optional_metric(row.get('figure_recall'))}`")
            lines.append(f"- Table recall: `{_format_optional_metric(row.get('table_recall'))}`")
        intrinsic = row.get("intrinsic_metrics") or {}
        lines.append(f"- Duplicate headings: `{intrinsic.get('duplicate_heading_count', 0)}`")
        lines.append(f"- Empty sections: `{intrinsic.get('empty_section_count', 0)}`")
        lines.append(f"- Consecutive heading runs: `{intrinsic.get('consecutive_heading_run_count', 0)}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def score_outputs(docs: Sequence[BenchmarkDoc], *, systems: Sequence[str] = SYSTEMS) -> Dict[str, Any]:
    ensure_dirs()
    rows: List[Dict[str, Any]] = []
    for doc in docs:
        gold = load_gold_doc(doc.doc_id)
        for system in systems:
            normalized = read_json(normalized_doc_path(system, doc.doc_id))
            if not normalized:
                raise FileNotFoundError(f"Normalized output missing for {system}/{doc.doc_id}")
            rows.append(score_normalized_doc(normalized, gold, doc))

    summary = _aggregate_rows(rows)
    report = {
        "rows": rows,
        "summary": summary,
    }
    write_json(REPORT_DIR / "summary.json", report)
    (REPORT_DIR / "summary.md").write_text(_render_markdown_report(rows, summary), encoding="utf-8")
    write_json(RUN_DIR / "latest_scores.json", report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score normalized benchmark outputs.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument("--systems", nargs="*", default=list(SYSTEMS), choices=list(SYSTEMS))
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)
    report = score_outputs(docs, systems=args.systems)
    print(f"[score] scored {len(report['rows'])} system-document pair(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
