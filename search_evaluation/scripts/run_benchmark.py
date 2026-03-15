from __future__ import annotations

import asyncio
import json
import math
import statistics
import time
from typing import Any, Dict, List, Optional

from _common import (
    GOLD_PATH,
    IMPORT_MANIFEST_PATH,
    METADATA_PATH,
    QUERIES_PATH,
    REPORT_DIR,
    RUN_DIR,
    eval_conn_factory,
    ensure_dirs,
    read_jsonl,
)


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    idx = (len(values) - 1) * p
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return values[lower]
    frac = idx - lower
    return values[lower] + (values[upper] - values[lower]) * frac


def _set_eval_context() -> Any:
    from backend import main as backend_main
    from backend.core.search import configure_connection_factory

    def _get_eval_conn():
        import sqlite3
        from _common import EVAL_DB_PATH

        conn = sqlite3.connect(EVAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    configure_connection_factory(eval_conn_factory)
    backend_main.get_conn = _get_eval_conn
    return backend_main


async def _pgvector_search_section_hits_async(
    backend_main: Any,
    *,
    store: Any,
    pool: Any,
    query: str,
    paper_ids: List[int],
    limit: int,
) -> List[Dict[str, Any]]:
    alpha_raw = backend_main.os.getenv("HYBRID_SEARCH_ALPHA", "0.5")
    try:
        alpha = float(alpha_raw)
    except ValueError:
        alpha = 0.5

    retrieve_k = max(20, min(limit * 5, 300))
    results = await backend_main.hybrid_search(query, store, pool, k=retrieve_k, paper_ids=paper_ids, alpha=alpha)
    if not results:
        return []

    tokens = backend_main._query_tokens(query)
    page_scores: Dict[tuple[int, int], float] = {}
    page_best: Dict[tuple[int, int], Dict[str, Any]] = {}
    page_best_match: Dict[tuple[int, int], Dict[str, Any]] = {}

    for idx, row in enumerate(results):
        pid = row.get("paper_id")
        if pid is None:
            continue
        match_block = backend_main._select_block_for_query(row, tokens, query)
        page_no = match_block.get("page_no") or row.get("page_no")
        if not page_no:
            continue
        raw_score = backend_main._pgvector_score(row)
        semantic_score = backend_main._rrf_score(idx, k=15) + min(max(raw_score, 0.0), 1.0) * 0.15
        key = (int(pid), int(page_no))
        row_block_index = backend_main._coalesce_not_none(match_block.get("block_index"), row.get("block_index"))
        row_bbox = backend_main._coalesce_not_none(match_block.get("bbox"), row.get("bbox"))
        row_text = match_block.get("text") or row.get("text")
        row_lex_hits = int(match_block.get("lex_hits") or 0)
        row_match_score = float(match_block.get("match_score") or 0.0)
        row_exact_phrase = bool(match_block.get("exact_phrase") or False)
        row_section_canonical = str(match_block.get("section_canonical") or "")

        prev = page_scores.get(key)
        if prev is None or semantic_score > prev:
            page_scores[key] = semantic_score
            page_best[key] = {
                "bbox": row_bbox,
                "block_index": row_block_index,
                "text": row_text,
                "lex_hits": row_lex_hits,
                "match_score": row_match_score,
                "exact_phrase": row_exact_phrase,
                "section_canonical": row_section_canonical,
                "semantic_score": semantic_score,
                "semantic_raw_score": raw_score,
            }

        prev_match = page_best_match.get(key)
        if prev_match is None:
            page_best_match[key] = dict(page_best[key])
        else:
            prev_key = (
                bool(prev_match.get("exact_phrase")),
                float(prev_match.get("match_score") or 0.0),
                int(prev_match.get("lex_hits") or 0),
                float(prev_match.get("semantic_score") or 0.0),
            )
            curr_key = (
                row_exact_phrase,
                row_match_score,
                row_lex_hits,
                semantic_score,
            )
            if curr_key > prev_key:
                page_best_match[key] = {
                    "bbox": row_bbox,
                    "block_index": row_block_index,
                    "text": row_text,
                    "lex_hits": row_lex_hits,
                    "match_score": row_match_score,
                    "exact_phrase": row_exact_phrase,
                    "section_canonical": row_section_canonical,
                    "semantic_score": semantic_score,
                    "semantic_raw_score": raw_score,
                }

    if not page_scores:
        return []

    paper_list = sorted({paper_id for paper_id, _ in page_scores.keys()})
    page_list = sorted({page_no for _, page_no in page_scores.keys()})
    paper_placeholders = ",".join("?" for _ in paper_list)
    page_placeholders = ",".join("?" for _ in page_list)
    with backend_main.get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, paper_id, page_no, text
            FROM sections
            WHERE paper_id IN ({paper_placeholders}) AND page_no IN ({page_placeholders})
            """,
            (*paper_list, *page_list),
        ).fetchall()

    sections: List[Dict[str, Any]] = []
    for row in rows:
        key = (int(row["paper_id"]), int(row["page_no"]))
        if key not in page_scores:
            continue
        best = page_best.get(key) or {}
        matched = page_best_match.get(key)
        if matched and tokens:
            min_hits = 1 if len(tokens) <= 3 else 2
            if bool(matched.get("exact_phrase")) or int(matched.get("lex_hits", 0)) >= min_hits:
                best = matched
        search_bucket = backend_main._infer_search_section_bucket(
            str((row["text"] or "") or best.get("text") or ""),
            page_no=int(row["page_no"]),
            section_canonical=best.get("section_canonical"),
        )
        best_text = str(best.get("text") or "")
        entry: Dict[str, Any] = {
            "id": int(row["id"]),
            "page_no": int(row["page_no"]),
            "paper_id": int(row["paper_id"]),
            "match_score": page_scores.get(key, 0.0) * backend_main._section_bucket_multiplier(search_bucket),
            "keyword_score": 0.0,
            "semantic_score": float(best.get("semantic_score") or page_scores.get(key, 0.0)),
            "semantic_raw_score": float(best.get("semantic_raw_score") or 0.0),
            "block_match_score": float(best.get("match_score") or 0.0),
            "lex_hits": int(best.get("lex_hits") or 0),
            "exact_phrase": bool(best.get("exact_phrase") or False),
            "match_bbox": best.get("bbox"),
            "match_block_index": best.get("block_index"),
            "match_section_canonical": best.get("section_canonical"),
            "search_bucket": search_bucket,
            "source_text": best_text,
        }
        match_text = backend_main._build_match_snippet(query, tokens, best_text)
        if match_text:
            entry["match_text"] = match_text
        sections.append(entry)

    sections.sort(key=lambda item: item.get("match_score", 0.0), reverse=True)
    return sections[:limit]


async def _run_query_async(backend_main: Any, store: Any, pool: Any, query: str, paper_ids: List[int]) -> Dict[str, Any]:
    start = time.perf_counter()
    keyword_hits = backend_main._keyword_section_hits(
        query,
        paper_ids,
        include_text=False,
        max_chars=None,
        limit=300,
    )
    semantic_hits = await _pgvector_search_section_hits_async(
        backend_main,
        store=store,
        pool=pool,
        query=query,
        paper_ids=paper_ids,
        limit=300,
    )
    section_hits = backend_main._merge_section_hits(keyword_hits, semantic_hits, limit=300)
    section_hits = backend_main._filter_section_hits_for_query(query, section_hits)
    title_bonus_by_id = backend_main._paper_title_bonus_lookup(query, limit=100)
    aggregated = backend_main._aggregate_section_hits_to_papers(section_hits, title_bonus_by_id)
    aggregated = backend_main._inject_title_only_candidates(aggregated, title_bonus_by_id)
    aggregated = backend_main._filter_aggregated_papers_for_query(query, aggregated)
    ranking = sorted(
        (
            {
                "paper_id": pid,
                "score": meta["score"],
                "best_hit": meta["best_hit"],
                "support_hits": meta["support_hits"],
            }
            for pid, meta in aggregated.items()
        ),
        key=lambda item: float(item["score"]),
        reverse=True,
    )
    latency_ms = (time.perf_counter() - start) * 1000.0
    return {
        "query": query,
        "latency_ms": latency_ms,
        "ranking": ranking,
    }


def _evaluate_result(result: Dict[str, Any], gold: Dict[str, Any]) -> Dict[str, Any]:
    expected_ids = [int(pid) for pid in gold.get("expected_paper_ids") or []]
    ranking = result["ranking"]
    ranked_ids = [int(item["paper_id"]) for item in ranking]
    top_id = ranked_ids[0] if ranked_ids else None
    is_no_match = bool(gold.get("is_no_match"))

    if is_no_match:
        paper_ok = not ranked_ids
        reciprocal_rank = 1.0 if paper_ok else 0.0
    else:
        paper_ok = top_id in expected_ids
        reciprocal_rank = 0.0
        for idx, pid in enumerate(ranked_ids):
            if pid in expected_ids:
                reciprocal_rank = 1.0 / float(idx + 1)
                break

    top_hit = ranking[0]["best_hit"] if ranking else {}
    gold_pages = [int(page) for page in gold.get("gold_pages") or []]
    gold_sections = [str(section) for section in gold.get("gold_section_canonicals") or []]
    page_hit = bool(gold_pages) and int(top_hit.get("page_no") or -1) in gold_pages
    section_hit = bool(gold_sections) and str(top_hit.get("match_section_canonical") or "") in gold_sections

    return {
        "query_id": gold["query_id"],
        "query": gold["query"],
        "query_type": gold.get("query_type"),
        "expected_paper_ids": expected_ids,
        "ranked_paper_ids": ranked_ids[:5],
        "top_paper_id": top_id,
        "paper_hit_at_1": paper_ok,
        "paper_hit_at_3": any(pid in expected_ids for pid in ranked_ids[:3]) if expected_ids else paper_ok,
        "paper_hit_at_5": any(pid in expected_ids for pid in ranked_ids[:5]) if expected_ids else paper_ok,
        "reciprocal_rank": reciprocal_rank,
        "page_hit_at_1": page_hit,
        "section_hit_at_1": section_hit,
        "latency_ms": result["latency_ms"],
        "top_hit": top_hit,
        "notes": gold.get("notes"),
    }


def _build_markdown_report(
    metadata_rows: List[Dict[str, Any]],
    gold_rows: List[Dict[str, Any]],
    evaluated_rows: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> str:
    by_id = {int(row["paper_id"]): row for row in metadata_rows}
    query_count = len(gold_rows)
    no_match_count = sum(1 for row in gold_rows if row.get("is_no_match"))
    positive_count = query_count - no_match_count
    lines = [
        "# Search Baseline Report",
        "",
        "Current system under test: unified hybrid library search.",
        "",
        "## Benchmark Construction",
        "",
        "- corpus source: recent arXiv PDFs downloaded into `search_evaluation/pdfs/`",
        "- corpus size: 20 papers across `cs.AI`, `cs.LG`, `cs.CL`, and `cs.CV`",
        f"- query count: {query_count}",
        f"- positive queries: {positive_count}",
        f"- no-match queries: {no_match_count}",
        "- gold set quality: manually curated from the downloaded PDFs using the review notes in `search_evaluation/reviews/`",
        "- gold fields: expected paper, expected page when confident, expected section canonical when the extracted section map was reliable",
        "",
        "This benchmark is intentionally paper-retrieval first. Page and section metrics are included as secondary localization checks.",
        "",
        "## Corpus",
        "",
        f"- papers: `{len(metadata_rows)}`",
        f"- queries: `{len(gold_rows)}`",
        "",
        "### Papers",
        "",
    ]
    for row in metadata_rows:
        lines.append(f"- `{row['paper_id']}` `{row['arxiv_id']}`: {row['title']}")

    lines.extend(
        [
            "",
            "## Aggregate Metrics",
            "",
            f"- hit_at_1: `{summary['hit_at_1']:.3f}`",
            f"- hit_at_3: `{summary['hit_at_3']:.3f}`",
            f"- hit_at_5: `{summary['hit_at_5']:.3f}`",
            f"- mrr: `{summary['mrr']:.3f}`",
            f"- no_match_accuracy: `{summary['no_match_accuracy']:.3f}`",
            f"- page_hit_at_1: `{summary['page_hit_at_1']:.3f}`",
            f"- section_hit_at_1: `{summary['section_hit_at_1']:.3f}`",
            f"- latency_mean_ms: `{summary['latency_mean_ms']:.1f}`",
            f"- latency_p50_ms: `{summary['latency_p50_ms']:.1f}`",
            f"- latency_p95_ms: `{summary['latency_p95_ms']:.1f}`",
            "",
            "## Per-Query Results",
            "",
            "| Query | Type | Top Paper | Correct | Page Hit | Section Hit |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in evaluated_rows:
        top = by_id.get(int(row["top_paper_id"])) if row.get("top_paper_id") is not None else None
        top_label = top["title"] if top else "None"
        lines.append(
            f"| {row['query']} | {row.get('query_type') or ''} | {top_label} | "
            f"{'yes' if row['paper_hit_at_1'] else 'no'} | "
            f"{'yes' if row['page_hit_at_1'] else 'no'} | "
            f"{'yes' if row['section_hit_at_1'] else 'no'} |"
        )

    failures = [row for row in evaluated_rows if not row["paper_hit_at_1"]]
    lines.extend(
        [
            "",
            "## Takeaways",
            "",
            f"- Top-1 paper accuracy is `{summary['hit_at_1']:.3f}` on this benchmark.",
            f"- No-match accuracy is `{summary['no_match_accuracy']:.3f}` on the unsupported-query slice.",
            f"- Page localization is weak at `{summary['page_hit_at_1']:.3f}`.",
            f"- Section localization is better than page localization but still limited at `{summary['section_hit_at_1']:.3f}`.",
            "",
            "## Failure Cases",
            "",
        ]
    )
    if not failures:
        lines.append("- none")
    else:
        for row in failures:
            expected = ", ".join(str(pid) for pid in row["expected_paper_ids"]) or "no result"
            predicted = ", ".join(str(pid) for pid in row["ranked_paper_ids"]) or "no result"
            lines.append(
                f"- `{row['query']}` expected `{expected}` but got `{predicted}`"
            )
    return "\n".join(lines) + "\n"


async def _main_async() -> None:
    ensure_dirs()
    if not IMPORT_MANIFEST_PATH.exists():
        raise RuntimeError("No import manifest found. Run build_eval_corpus.py first.")

    metadata_rows = read_jsonl(METADATA_PATH)
    gold_rows = read_jsonl(GOLD_PATH)
    if not gold_rows:
        raise RuntimeError("No gold.jsonl found. Curate the benchmark gold set first.")

    backend_main = _set_eval_context()
    pool = await backend_main.get_pg_pool()
    store = backend_main.PgVectorStore(pool)
    paper_ids = [int(row["paper_id"]) for row in metadata_rows]

    evaluated_rows: List[Dict[str, Any]] = []
    latencies: List[float] = []
    no_match_rows = 0
    no_match_ok = 0
    page_rows = 0
    page_ok = 0
    section_rows = 0
    section_ok = 0

    for gold in gold_rows:
        result = await _run_query_async(backend_main, store, pool, str(gold["query"]), paper_ids)
        eval_row = _evaluate_result(result, gold)
        evaluated_rows.append(eval_row)
        latencies.append(float(eval_row["latency_ms"]))
        if gold.get("is_no_match"):
            no_match_rows += 1
            if eval_row["paper_hit_at_1"]:
                no_match_ok += 1
        if gold.get("gold_pages"):
            page_rows += 1
            if eval_row["page_hit_at_1"]:
                page_ok += 1
        if gold.get("gold_section_canonicals"):
            section_rows += 1
            if eval_row["section_hit_at_1"]:
                section_ok += 1

    summary = {
        "hit_at_1": sum(1 for row in evaluated_rows if row["paper_hit_at_1"]) / len(evaluated_rows),
        "hit_at_3": sum(1 for row in evaluated_rows if row["paper_hit_at_3"]) / len(evaluated_rows),
        "hit_at_5": sum(1 for row in evaluated_rows if row["paper_hit_at_5"]) / len(evaluated_rows),
        "mrr": sum(float(row["reciprocal_rank"]) for row in evaluated_rows) / len(evaluated_rows),
        "no_match_accuracy": (no_match_ok / no_match_rows) if no_match_rows else 0.0,
        "page_hit_at_1": (page_ok / page_rows) if page_rows else 0.0,
        "section_hit_at_1": (section_ok / section_rows) if section_rows else 0.0,
        "latency_mean_ms": statistics.fmean(latencies) if latencies else 0.0,
        "latency_p50_ms": _percentile(sorted(latencies), 0.50),
        "latency_p95_ms": _percentile(sorted(latencies), 0.95),
    }

    run_path = RUN_DIR / "benchmark_results.jsonl"
    report_path = REPORT_DIR / "SEARCH_BASELINE_REPORT.md"
    summary_path = REPORT_DIR / "summary.json"
    run_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True) for row in evaluated_rows) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(
        _build_markdown_report(metadata_rows, gold_rows, evaluated_rows, summary),
        encoding="utf-8",
    )
    QUERIES_PATH.write_text(
        "\n".join(
            json.dumps(
                {
                    "query_id": row["query_id"],
                    "query": row["query"],
                    "query_type": row.get("query_type"),
                },
                ensure_ascii=True,
            )
            for row in gold_rows
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"report_path": str(report_path), "summary": summary}, indent=2))
    await backend_main.close_pg_pool()


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
