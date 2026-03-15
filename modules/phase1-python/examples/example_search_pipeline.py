#!/usr/bin/env python3
from __future__ import annotations

"""
Minimal runnable example for `ia_phase1.search_pipeline`.

What this shows:
- how to configure the pipeline's SQLite dependency
- how to provide keyword + semantic section-hit callbacks
- how to run the full unified search flow

Run:
    cd modules/phase1-python
    python examples/example_search_pipeline.py
    python examples/example_search_pipeline.py "vision benchmark"

This uses:
- real SQLite FTS keyword search from `ia_phase1.search_keyword`
- a tiny toy semantic callback for demonstration only

The semantic callback here is intentionally simple. In a real app, replace it with
pgvector / embedding retrieval and return the same hit structure.
"""

import json
import sqlite3
import sys
from contextlib import contextmanager
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ia_phase1.search_context import build_match_snippet, query_tokens
from ia_phase1.search_keyword import (
    configure_connection_factory as configure_keyword_connection_factory,
    search_sections,
)
from ia_phase1.search_pipeline import (
    aggregate_section_hits_to_papers,
    configure_connection_factory as configure_pipeline_connection_factory,
    filter_aggregated_papers_for_query,
    filter_section_hits_for_query,
    infer_search_section_bucket,
    inject_title_only_candidates,
    paper_title_bonus_lookup,
    rrf_score,
    search_section_hits_unified,
    token_overlap,
)


def build_demo_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE papers(
            id INTEGER PRIMARY KEY,
            title TEXT,
            source_url TEXT,
            pdf_path TEXT,
            rag_status TEXT,
            rag_error TEXT,
            rag_updated_at TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE sections(
            id INTEGER PRIMARY KEY,
            paper_id INTEGER,
            page_no INTEGER,
            text TEXT
        )
        """
    )
    conn.execute("CREATE VIRTUAL TABLE sections_fts USING fts5(text, paper_id, page_no)")

    papers = [
        (
            1,
            "Large Language Models for Planning",
            "https://arxiv.org/abs/2501.00001",
            "/tmp/paper1.pdf",
            "indexed",
            None,
            None,
            "2026-01-01",
        ),
        (
            2,
            "Vision Benchmarking with Prompt Tuning",
            "https://arxiv.org/abs/2501.00002",
            "/tmp/paper2.pdf",
            "indexed",
            None,
            None,
            "2026-01-02",
        ),
        (
            3,
            "Reference Survey of Older Systems",
            "https://arxiv.org/abs/2501.00003",
            "/tmp/paper3.pdf",
            "indexed",
            None,
            None,
            "2026-01-03",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        papers,
    )

    sections = [
        (101, 1, 2, "Large language models improve planning through better decomposition and reasoning."),
        (102, 1, 4, "We evaluate task planning performance across difficult long-horizon tasks."),
        (201, 2, 3, "Prompt tuning improves vision benchmark performance for image understanding."),
        (202, 2, 5, "Benchmark results show strong gains on vision-language tasks."),
        (301, 3, 9, "References [1] language model benchmark 2024 conference proceedings."),
    ]
    conn.executemany("INSERT INTO sections(id, paper_id, page_no, text) VALUES(?,?,?,?)", sections)
    conn.executemany(
        "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
        [(sid, text, str(pid), str(page_no)) for sid, pid, page_no, text in sections],
    )
    conn.commit()
    return conn


@contextmanager
def connection_factory(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    yield conn


def keyword_section_hits_fn(
    query: str,
    paper_ids: Optional[List[int]] = None,
    *,
    include_text: bool,
    max_chars: Optional[int],
    limit: int,
) -> List[Dict[str, Any]]:
    rows = search_sections(query, search_type="keyword", paper_ids=paper_ids, limit=limit)
    tokens = query_tokens(query)
    query_l = query.strip().lower()
    hits: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        text = str(row["text"] or "")
        lex_hits = token_overlap(tokens, text)
        exact_phrase = bool(query_l and query_l in text.lower())
        keyword_score = rrf_score(idx, k=10)
        if exact_phrase:
            keyword_score += 0.08
        keyword_score += min(lex_hits, 4) * 0.015
        entry: Dict[str, Any] = {
            "id": int(row["id"]),
            "paper_id": int(row["paper_id"]),
            "page_no": int(row["page_no"]),
            "match_score": keyword_score,
            "keyword_score": keyword_score,
            "semantic_score": 0.0,
            "semantic_raw_score": 0.0,
            "block_match_score": float(lex_hits) + (8.0 if exact_phrase else 0.0),
            "lex_hits": lex_hits,
            "exact_phrase": exact_phrase,
            "match_section_canonical": None,
            "search_bucket": infer_search_section_bucket(text, page_no=int(row["page_no"])),
            "source_text": text,
            "match_text": build_match_snippet(query, tokens, text),
        }
        if include_text:
            entry["text"] = text[:max_chars] if max_chars else text
        hits.append(entry)
    return hits


def semantic_section_hits_fn(
    query: str,
    search_type: str,
    paper_ids: Optional[List[int]] = None,
    *,
    include_text: bool,
    max_chars: Optional[int],
    limit: int,
) -> List[Dict[str, Any]]:
    _ = search_type
    tokens = query_tokens(query)
    query_l = query.lower()

    with DEMO_CONN:
        params: List[Any] = []
        sql = "SELECT id, paper_id, page_no, text FROM sections"
        if paper_ids:
            placeholders = ",".join("?" for _ in paper_ids)
            sql += f" WHERE paper_id IN ({placeholders})"
            params.extend(paper_ids)
        sql += " ORDER BY id ASC"
        rows = DEMO_CONN.execute(sql, tuple(params)).fetchall()

    scored: List[Dict[str, Any]] = []
    for row in rows:
        text = str(row["text"] or "")
        similarity = SequenceMatcher(None, query_l, text.lower()[: max(len(query_l) * 3, 120)]).ratio()
        if similarity < 0.10:
            continue
        lex_hits = token_overlap(tokens, text)
        semantic_score = rrf_score(len(scored), k=15) + min(max(similarity, 0.0), 1.0) * 0.15
        entry: Dict[str, Any] = {
            "id": int(row["id"]),
            "paper_id": int(row["paper_id"]),
            "page_no": int(row["page_no"]),
            "match_score": semantic_score,
            "keyword_score": 0.0,
            "semantic_score": semantic_score,
            "semantic_raw_score": similarity,
            "block_match_score": float(lex_hits),
            "lex_hits": lex_hits,
            "exact_phrase": bool(query_l and query_l in text.lower()),
            "match_section_canonical": None,
            "search_bucket": infer_search_section_bucket(text, page_no=int(row["page_no"])),
            "source_text": text,
            "match_text": build_match_snippet(query, tokens, text),
        }
        if include_text:
            entry["text"] = text[:max_chars] if max_chars else text
        scored.append(entry)

    scored.sort(key=lambda item: float(item["semantic_raw_score"]), reverse=True)
    return scored[:limit]


def render_ranked_papers(aggregated: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not aggregated:
        return []

    ranked_ids = [
        pid
        for pid, _meta in sorted(
            aggregated.items(),
            key=lambda item: float(item[1].get("score", 0.0)),
            reverse=True,
        )
    ]
    placeholders = ",".join("?" for _ in ranked_ids)
    rows = DEMO_CONN.execute(
        f"SELECT id, title, source_url FROM papers WHERE id IN ({placeholders})",
        tuple(ranked_ids),
    ).fetchall()
    by_id = {int(row["id"]): dict(row) for row in rows}

    rendered: List[Dict[str, Any]] = []
    for pid in ranked_ids:
        meta = aggregated[pid]
        paper = by_id.get(pid, {"id": pid, "title": f"Paper {pid}", "source_url": None})
        best_hit = meta.get("best_hit") or {}
        rendered.append(
            {
                "paper_id": pid,
                "title": paper["title"],
                "source_url": paper.get("source_url"),
                "score": round(float(meta.get("score", 0.0)), 4),
                "title_bonus": round(float(meta.get("title_bonus", 0.0)), 4),
                "page_no": best_hit.get("page_no"),
                "match_text": best_hit.get("match_text"),
            }
        )
    return rendered


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "large language model planning"
    search_type = sys.argv[2] if len(sys.argv) > 2 else "hybrid"

    section_hits = search_section_hits_unified(
        query,
        search_type,
        keyword_section_hits_fn=keyword_section_hits_fn,
        semantic_section_hits_fn=semantic_section_hits_fn,
        include_text=False,
        max_chars=None,
        limit=25,
    )
    filtered_hits = filter_section_hits_for_query(query, section_hits)
    title_bonus_by_id = paper_title_bonus_lookup(query, limit=25)
    aggregated = aggregate_section_hits_to_papers(filtered_hits, title_bonus_by_id)
    aggregated = inject_title_only_candidates(aggregated, title_bonus_by_id)
    aggregated = filter_aggregated_papers_for_query(query, aggregated)

    payload = {
        "query": query,
        "search_type": search_type,
        "section_hits": filtered_hits,
        "ranked_papers": render_ranked_papers(aggregated),
    }
    print(json.dumps(payload, indent=2))


DEMO_CONN = build_demo_connection()
configure_keyword_connection_factory(lambda: connection_factory(DEMO_CONN))
configure_pipeline_connection_factory(lambda: connection_factory(DEMO_CONN))


if __name__ == "__main__":
    main()
