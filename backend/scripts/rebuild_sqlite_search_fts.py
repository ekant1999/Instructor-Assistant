from __future__ import annotations

import sqlite3
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.database import DB_PATH, get_conn, rebuild_fts_tables


def _count(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"] if row is not None else 0)


def _sanity_match(conn: sqlite3.Connection, query: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM sections_fts WHERE sections_fts MATCH ?",
        (query,),
    ).fetchone()
    return int(row["count"] if row is not None else 0)


def main() -> None:
    db_path = Path(DB_PATH).resolve()
    print(f"Rebuilding SQLite FTS indexes in {db_path}")
    rebuild_fts_tables()
    with get_conn() as conn:
        base_counts = {
            "papers": _count(conn, "papers"),
            "sections": _count(conn, "sections"),
            "notes": _count(conn, "notes"),
            "summaries": _count(conn, "summaries"),
        }
        fts_counts = {
            "papers_fts": _count(conn, "papers_fts"),
            "sections_fts": _count(conn, "sections_fts"),
            "notes_fts": _count(conn, "notes_fts"),
            "summaries_fts": _count(conn, "summaries_fts"),
        }
        sanity = {
            "MATCH('LLM')": _sanity_match(conn, "LLM"),
            "MATCH('planning')": _sanity_match(conn, "planning"),
        }

    print("Base row counts:")
    for table, count in base_counts.items():
        print(f"  {table}: {count}")
    print("FTS row counts:")
    for table, count in fts_counts.items():
        print(f"  {table}: {count}")
    print("MATCH sanity checks:")
    for label, count in sanity.items():
        print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
