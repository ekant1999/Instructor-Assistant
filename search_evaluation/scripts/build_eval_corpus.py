from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from _common import EVAL_DB_PATH, IMPORT_MANIFEST_PATH, METADATA_PATH, ensure_dirs, read_jsonl


def init_eval_db() -> sqlite3.Connection:
    if EVAL_DB_PATH.exists():
        EVAL_DB_PATH.unlink()
    conn = sqlite3.connect(EVAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE papers(
          id INTEGER PRIMARY KEY,
          title TEXT,
          source_url TEXT,
          pdf_path TEXT NOT NULL,
          rag_status TEXT,
          rag_error TEXT,
          rag_updated_at TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE sections(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_id INTEGER NOT NULL,
          page_no INTEGER NOT NULL,
          text TEXT,
          FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE papers_fts USING fts5(
            title,
            source_url
        );
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE sections_fts USING fts5(
            text,
            paper_id,
            page_no
        );
        """
    )
    conn.commit()
    return conn


async def build_eval_corpus(skip_pg: bool = False) -> Dict[str, Any]:
    from backend.core.pdf import extract_pages
    from backend.core.postgres import close_pool, get_pool
    from backend.rag.ingest_pgvector import ingest_single_paper

    metadata = read_jsonl(METADATA_PATH)
    if not metadata:
        raise RuntimeError("No metadata found. Run fetch_arxiv_papers.py first.")

    ensure_dirs()
    conn = init_eval_db()
    manifest: List[Dict[str, Any]] = []

    pool = None
    if not skip_pg:
        pool = await get_pool()
        async with pool.acquire() as pg_conn:
            await pg_conn.execute(
                "DELETE FROM text_blocks WHERE paper_id = ANY($1::int[])",
                [int(row["paper_id"]) for row in metadata],
            )
            await pg_conn.execute(
                "DELETE FROM papers WHERE id = ANY($1::int[])",
                [int(row["paper_id"]) for row in metadata],
            )

    try:
        for row in metadata:
            paper_id = int(row["paper_id"])
            title = str(row["title"])
            source_url = f"https://arxiv.org/abs/{row['arxiv_id']}"
            pdf_path = Path(str(row["pdf_path"])).expanduser().resolve()
            conn.execute(
                """
                INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at)
                VALUES(?,?,?,?,?,?,datetime('now'),datetime('now'))
                """,
                (paper_id, title, source_url, str(pdf_path), "done", None),
            )
            conn.execute(
                "INSERT INTO papers_fts(rowid, title, source_url) VALUES(?,?,?)",
                (paper_id, title, source_url),
            )

            page_count = 0
            for page_no, text in extract_pages(pdf_path):
                cursor = conn.execute(
                    "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
                    (paper_id, int(page_no), text),
                )
                section_id = int(cursor.lastrowid)
                conn.execute(
                    "INSERT INTO sections_fts(rowid, text, paper_id, page_no) VALUES(?,?,?,?)",
                    (section_id, text, str(paper_id), str(page_no)),
                )
                page_count += 1
            conn.commit()

            ingest_result: Dict[str, Any] = {"skipped_pg": skip_pg}
            if not skip_pg:
                async with pool.acquire() as pg_conn:
                    await pg_conn.execute(
                        """
                        INSERT INTO papers(id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at)
                        VALUES($1, $2, $3, $4, 'done', NULL, NOW(), NOW())
                        """,
                        paper_id,
                        title,
                        source_url,
                        str(pdf_path),
                    )
                ingest_result = await ingest_single_paper(
                    pdf_path=str(pdf_path),
                    paper_id=paper_id,
                    paper_title=title,
                    source_url=source_url,
                )
            manifest.append(
                {
                    "paper_id": paper_id,
                    "arxiv_id": row["arxiv_id"],
                    "title": title,
                    "page_count": page_count,
                    "ingest_result": ingest_result,
                }
            )
    finally:
        conn.close()
        if pool is not None:
            await close_pool()

    IMPORT_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"papers": len(manifest), "manifest_path": str(IMPORT_MANIFEST_PATH)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build isolated eval SQLite corpus and pgvector index.")
    parser.add_argument("--skip-pg", action="store_true", help="Only build the eval SQLite DB.")
    args = parser.parse_args()
    ensure_dirs()
    result = asyncio.run(build_eval_corpus(skip_pg=args.skip_pg))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
