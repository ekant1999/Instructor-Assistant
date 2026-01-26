from __future__ import annotations

import sqlite3
from pathlib import Path

# Store backend data inside backend/data to keep services self-contained.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Ensure the base tables exist and run lightweight migrations (notes FK + question tables).
    """
    with get_conn() as conn:
        _init_core_tables(conn)
        _ensure_papers_rag_columns(conn)
        _ensure_notes_title_column(conn)
        _ensure_notes_tags_column(conn)
    _ensure_notes_fk_set_null()
    ensure_question_tables()


def _init_core_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS papers(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        CREATE TABLE IF NOT EXISTS sections(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_id INTEGER NOT NULL,
          page_no INTEGER NOT NULL,
          text TEXT,
          FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
        """
    )
    # Notes table uses SET NULL so notes don't get deleted when paper gets deletes in the UI path.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_id INTEGER NULL,
          body TEXT NOT NULL,
          title TEXT,
          tags_json TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE SET NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS summaries(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_id INTEGER NOT NULL,
          title TEXT,
          content TEXT NOT NULL,
          agent TEXT,
          style TEXT,
          word_count INTEGER,
          is_edited INTEGER DEFAULT 0,
          metadata_json TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_qna(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paper_id INTEGER NOT NULL,
          question TEXT NOT NULL,
          answer TEXT NOT NULL,
          sources_json TEXT,
          scope TEXT,
          provider TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def _ensure_papers_rag_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(papers)")}
    if "rag_status" not in columns:
        conn.execute("ALTER TABLE papers ADD COLUMN rag_status TEXT")
    if "rag_error" not in columns:
        conn.execute("ALTER TABLE papers ADD COLUMN rag_error TEXT")
    if "rag_updated_at" not in columns:
        conn.execute("ALTER TABLE papers ADD COLUMN rag_updated_at TEXT")
    conn.commit()


def _ensure_notes_title_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(notes)")}
    if "title" not in columns:
        conn.execute("ALTER TABLE notes ADD COLUMN title TEXT")
        conn.commit()


def _ensure_notes_tags_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(notes)")}
    if "tags_json" not in columns:
        conn.execute("ALTER TABLE notes ADD COLUMN tags_json TEXT")
        conn.commit()


def _ensure_notes_fk_set_null() -> None:
    """
    Migrate legacy notes table (ON DELETE CASCADE) to ON DELETE SET NULL.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='notes'"
        ).fetchone()
        ddl = row[0] if row else ""
        if "FOREIGN KEY" in ddl and "ON DELETE SET NULL" in ddl:
            return

        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NULL,
                title TEXT,
                tags_json TEXT,
                body TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(paper_id) REFERENCES papers(id) ON DELETE SET NULL
            );
        """
        )
        conn.execute(
            """
            INSERT INTO notes_new (id, paper_id, title, tags_json, body, created_at)
            SELECT id, paper_id, title, tags_json, body, created_at FROM notes;
        """
        )
        conn.execute("DROP TABLE IF EXISTS notes;")
        conn.execute("ALTER TABLE notes_new RENAME TO notes;")
        conn.execute("COMMIT")
        conn.execute("PRAGMA foreign_keys=ON")


def ensure_question_tables() -> None:
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS question_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                text TEXT NOT NULL,
                options_json TEXT,
                answer TEXT,
                explanation TEXT,
                reference TEXT,
                FOREIGN KEY(set_id) REFERENCES question_sets(id) ON DELETE CASCADE
            );
        """
        )
        conn.commit()
