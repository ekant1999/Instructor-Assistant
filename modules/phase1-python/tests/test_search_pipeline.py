from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ia_phase1.search_pipeline import (
    aggregate_section_hits_to_papers,
    configure_connection_factory,
    filter_aggregated_papers_for_query,
    filter_section_hits_for_query,
    infer_search_section_bucket,
    inject_title_only_candidates,
    merge_section_hits,
    paper_title_bonus_lookup,
    search_section_hits_unified,
)


def _build_conn() -> sqlite3.Connection:
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

    conn.execute(
        "INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (1, "Large Language Models for Planning", "https://arxiv.org/abs/1234.5678", "/tmp/a.pdf", "indexed", None, None, "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (2, "Vision Benchmarking", "https://example.com/vision", "/tmp/b.pdf", "indexed", None, None, "2026-01-02"),
    )
    conn.execute(
        "INSERT INTO sections(id, paper_id, page_no, text) VALUES(?,?,?,?)",
        (10, 1, 2, "Large language models improve planning through better decomposition."),
    )
    conn.execute(
        "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
        (10, "Large language models improve planning through better decomposition.", "1", "2"),
    )
    conn.execute(
        "INSERT INTO sections(id, paper_id, page_no, text) VALUES(?,?,?,?)",
        (11, 2, 9, "References [1] language models benchmark 2024 conference proceedings."),
    )
    conn.execute(
        "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
        (11, "References [1] language models benchmark 2024 conference proceedings.", "2", "9"),
    )
    conn.commit()
    return conn


@contextmanager
def _conn_factory(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    yield conn


def test_paper_title_bonus_lookup_scores_direct_title_matches() -> None:
    conn = _build_conn()
    try:
        configure_connection_factory(lambda: _conn_factory(conn))
        bonuses = paper_title_bonus_lookup("large language model", limit=10)
        assert 1 in bonuses
        assert bonuses[1] > 0.0
        assert 2 not in bonuses or bonuses[2] < bonuses[1]
    finally:
        conn.close()


def test_inject_title_only_candidates_rescues_strong_title_match() -> None:
    conn = _build_conn()
    try:
        configure_connection_factory(lambda: _conn_factory(conn))
        aggregated = inject_title_only_candidates({}, {1: 0.35, 2: 0.05})
        assert 1 in aggregated
        assert aggregated[1]["title_only_match"] is True
        assert aggregated[1]["best_hit"]["paper_id"] == 1
        assert 2 not in aggregated
    finally:
        conn.close()


def test_merge_and_filter_pipeline_prefers_body_support_over_reference_noise() -> None:
    conn = _build_conn()
    try:
        configure_connection_factory(lambda: _conn_factory(conn))
        merged = merge_section_hits(
            [
                {
                    "id": 10,
                    "paper_id": 1,
                    "page_no": 2,
                    "match_score": 0.18,
                    "keyword_score": 0.18,
                    "semantic_score": 0.0,
                    "lex_hits": 3,
                    "exact_phrase": False,
                    "search_bucket": "body",
                    "source_text": "Large language models improve planning through better decomposition.",
                }
            ],
            [
                {
                    "id": 11,
                    "paper_id": 2,
                    "page_no": 9,
                    "match_score": 0.28,
                    "keyword_score": 0.0,
                    "semantic_score": 0.28,
                    "semantic_raw_score": 0.01,
                    "block_match_score": 2.0,
                    "lex_hits": 1,
                    "exact_phrase": False,
                    "search_bucket": "references",
                    "source_text": "References [1] language models benchmark 2024 conference proceedings.",
                }
            ],
            limit=10,
        )
        filtered = filter_section_hits_for_query("large language model planning", merged)
        assert [hit["id"] for hit in filtered] == [10]
        aggregated = aggregate_section_hits_to_papers(filtered)
        kept = filter_aggregated_papers_for_query("large language model planning", aggregated)
        assert list(kept.keys()) == [1]
    finally:
        conn.close()


def test_search_section_hits_unified_uses_callbacks_and_hybrid_merge() -> None:
    hits = search_section_hits_unified(
        "vision benchmark",
        "hybrid",
        keyword_section_hits_fn=lambda *args, **kwargs: [
            {
                "id": 51,
                "paper_id": 5,
                "page_no": 3,
                "match_score": 0.18,
                "keyword_score": 0.18,
                "semantic_score": 0.0,
                "lex_hits": 2,
                "exact_phrase": True,
                "search_bucket": "body",
            }
        ],
        semantic_section_hits_fn=lambda *args, **kwargs: [
            {
                "id": 51,
                "paper_id": 5,
                "page_no": 3,
                "match_score": 0.22,
                "keyword_score": 0.0,
                "semantic_score": 0.22,
                "lex_hits": 1,
                "exact_phrase": False,
                "search_bucket": "body",
            }
        ],
        include_text=False,
        max_chars=None,
        limit=20,
    )
    assert len(hits) == 1
    assert hits[0]["id"] == 51
    assert hits[0]["match_score"] > 0.40


def test_infer_search_section_bucket_detects_reference_and_front_matter() -> None:
    assert infer_search_section_bucket("References\n[1] Proceedings of the Conference 2024.", page_no=8) == "references"
    assert infer_search_section_bucket("Title\nDepartment of Computer Science\nAbstract\nWe study...", page_no=1) == "front_matter"
    assert infer_search_section_bucket("Method overview and results discussion", page_no=3) == "body"
