from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ia_phase1.search_keyword import (
    search_all,
    search_notes,
    search_papers,
    search_sections,
    search_summaries,
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
    conn.execute(
        """
        CREATE TABLE notes(
            id INTEGER PRIMARY KEY,
            paper_id INTEGER,
            title TEXT,
            body TEXT,
            tags_json TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE summaries(
            id INTEGER PRIMARY KEY,
            paper_id INTEGER,
            title TEXT,
            content TEXT,
            agent TEXT,
            style TEXT,
            word_count INTEGER,
            is_edited INTEGER,
            metadata_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    conn.execute("CREATE VIRTUAL TABLE papers_fts USING fts5(title, source_url)")
    conn.execute("CREATE VIRTUAL TABLE sections_fts USING fts5(text, paper_id, page_no)")
    conn.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(title, body, tags_json, paper_id)")
    conn.execute("CREATE VIRTUAL TABLE summaries_fts USING fts5(title, content, paper_id)")

    conn.execute(
        "INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (1, "Petri Net Relaxation Planning", "https://arxiv.org/abs/1234.5678", "/tmp/a.pdf", "indexed", None, None, "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO papers_fts(rowid, title, source_url) VALUES(?,?,?)",
        (1, "Petri Net Relaxation Planning", "https://arxiv.org/abs/1234.5678"),
    )

    conn.execute(
        "INSERT INTO sections(id, paper_id, page_no, text) VALUES(?,?,?,?)",
        (10, 1, 2, "We define one-shot and then sequential planning as a process."),
    )
    conn.execute(
        "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
        (10, "We define one-shot and then sequential planning as a process.", "1", "2"),
    )

    conn.execute(
        "INSERT INTO notes(id, paper_id, title, body, tags_json, created_at) VALUES(?,?,?,?,?,?)",
        (20, 1, "Planning note", "Sequential planning details", '["planning"]', "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO notes_fts(rowid, title, body, tags_json, paper_id) VALUES(?,?,?,?,?)",
        (20, "Planning note", "Sequential planning details", '["planning"]', "1"),
    )

    conn.execute(
        """
        INSERT INTO summaries(
            id, paper_id, title, content, agent, style, word_count, is_edited, metadata_json, created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (30, 1, "Planning summary", "This paper studies sequential planning.", "assistant", "concise", 120, 0, "{}", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO summaries_fts(rowid, title, content, paper_id) VALUES(?,?,?,?)",
        (30, "Planning summary", "This paper studies sequential planning.", "1"),
    )
    conn.commit()
    return conn


@contextmanager
def _conn_factory(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    yield conn


def test_search_keyword_functions_return_expected_rows() -> None:
    conn = _build_conn()
    try:
        factory = lambda: _conn_factory(conn)
        papers = search_papers("planning", get_conn_fn=factory, limit=5)
        sections = search_sections("sequential planning", get_conn_fn=factory, paper_ids=[1], limit=5)
        notes = search_notes("planning", get_conn_fn=factory, paper_ids=[1], limit=5)
        summaries = search_summaries("planning", get_conn_fn=factory, paper_ids=[1], limit=5)

        assert papers and papers[0]["id"] == 1
        assert sections and sections[0]["id"] == 10
        assert notes and notes[0]["id"] == 20
        assert summaries and summaries[0]["id"] == 30
    finally:
        conn.close()


def test_search_all_aggregates_all_categories() -> None:
    conn = _build_conn()
    try:
        factory = lambda: _conn_factory(conn)
        result = search_all("planning", get_conn_fn=factory, paper_ids=[1], limit_per_category=5)
        assert result["papers"]
        assert result["sections"]
        assert result["notes"]
        assert result["summaries"]
    finally:
        conn.close()


def test_search_sections_boundary_fallback_recovers_short_acronym_plural() -> None:
    conn = _build_conn()
    try:
        conn.execute(
            "INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (2, "Prompt Tuning for Vision-Language Models", "https://arxiv.org/abs/9999.0001", "/tmp/b.pdf", "indexed", None, None, "2026-01-02"),
        )
        conn.execute(
            "INSERT INTO papers_fts(rowid, title, source_url) VALUES(?,?,?)",
            (2, "Prompt Tuning for Vision-Language Models", "https://arxiv.org/abs/9999.0001"),
        )
        conn.execute(
            "INSERT INTO sections(id, paper_id, page_no, text) VALUES(?,?,?,?)",
            (11, 2, 4, "Prompt tuning in VLMs often borrows hard prompt templates used in LLMs or CLIP."),
        )
        conn.execute(
            "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
            (11, "Prompt tuning in VLMs often borrows hard prompt templates used in LLMs or CLIP.", "2", "4"),
        )
        conn.execute(
            "INSERT INTO sections(id, paper_id, page_no, text) VALUES(?,?,?,?)",
            (12, 2, 5, "This smallmodel controller is unrelated to acronym search."),
        )
        conn.execute(
            "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
            (12, "This smallmodel controller is unrelated to acronym search.", "2", "5"),
        )
        conn.commit()

        factory = lambda: _conn_factory(conn)
        sections = search_sections("LLM", get_conn_fn=factory, limit=10)

        assert [row["id"] for row in sections] == [11]
        assert sections[0]["paper_id"] == 2
    finally:
        conn.close()
