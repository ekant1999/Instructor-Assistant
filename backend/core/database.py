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
    _ensure_fts_tables()


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


def _ensure_fts_tables() -> None:
    """
    Create FTS5 virtual tables for full-text keyword search on papers, sections, notes, and summaries.
    Also create triggers to keep FTS tables in sync with the main tables.
    """
    with get_conn() as conn:
        # Check if FTS tables already exist
        papers_fts_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'"
        ).fetchone()
        
        if not papers_fts_exists:
            # Create FTS5 virtual table for papers
            conn.execute(
                """
                CREATE VIRTUAL TABLE papers_fts USING fts5(
                    title,
                    source_url,
                    content='papers',
                    content_rowid='id'
                );
            """
            )
            
            # Populate FTS table with existing data
            conn.execute(
                """
                INSERT INTO papers_fts(rowid, title, source_url)
                SELECT id, title, COALESCE(source_url, '') FROM papers;
            """
            )
            
            # Create triggers to keep papers_fts in sync
            conn.execute(
                """
                CREATE TRIGGER papers_ai AFTER INSERT ON papers BEGIN
                    INSERT INTO papers_fts(rowid, title, source_url)
                    VALUES (new.id, new.title, COALESCE(new.source_url, ''));
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER papers_au AFTER UPDATE ON papers BEGIN
                    UPDATE papers_fts SET title=new.title, source_url=COALESCE(new.source_url, '')
                    WHERE rowid=old.id;
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER papers_ad AFTER DELETE ON papers BEGIN
                    DELETE FROM papers_fts WHERE rowid=old.id;
                END;
            """
            )
        
        # FTS for sections (PDF content)
        sections_fts_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sections_fts'"
        ).fetchone()
        
        if not sections_fts_exists:
            conn.execute(
                """
                CREATE VIRTUAL TABLE sections_fts USING fts5(
                    text,
                    paper_id UNINDEXED,
                    page_no UNINDEXED,
                    content='sections',
                    content_rowid='id'
                );
            """
            )
            
            conn.execute(
                """
                INSERT INTO sections_fts(rowid, text, paper_id, page_no)
                SELECT id, text, paper_id, page_no FROM sections;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER sections_ai AFTER INSERT ON sections BEGIN
                    INSERT INTO sections_fts(rowid, text, paper_id, page_no)
                    VALUES (new.id, new.text, new.paper_id, new.page_no);
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER sections_au AFTER UPDATE ON sections BEGIN
                    UPDATE sections_fts SET text=new.text, paper_id=new.paper_id, page_no=new.page_no
                    WHERE rowid=old.id;
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER sections_ad AFTER DELETE ON sections BEGIN
                    DELETE FROM sections_fts WHERE rowid=old.id;
                END;
            """
            )
        
        # FTS for notes
        notes_fts_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'"
        ).fetchone()
        
        if not notes_fts_exists:
            conn.execute(
                """
                CREATE VIRTUAL TABLE notes_fts USING fts5(
                    title,
                    body,
                    tags_json,
                    paper_id UNINDEXED,
                    content='notes',
                    content_rowid='id'
                );
            """
            )
            
            conn.execute(
                """
                INSERT INTO notes_fts(rowid, title, body, tags_json, paper_id)
                SELECT id, COALESCE(title, ''), body, COALESCE(tags_json, ''), paper_id FROM notes;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
                    INSERT INTO notes_fts(rowid, title, body, tags_json, paper_id)
                    VALUES (new.id, COALESCE(new.title, ''), new.body, COALESCE(new.tags_json, ''), new.paper_id);
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
                    UPDATE notes_fts SET title=COALESCE(new.title, ''), body=new.body, 
                           tags_json=COALESCE(new.tags_json, ''), paper_id=new.paper_id
                    WHERE rowid=old.id;
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
                    DELETE FROM notes_fts WHERE rowid=old.id;
                END;
            """
            )
        
        # FTS for summaries
        summaries_fts_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='summaries_fts'"
        ).fetchone()
        
        if not summaries_fts_exists:
            conn.execute(
                """
                CREATE VIRTUAL TABLE summaries_fts USING fts5(
                    title,
                    content,
                    paper_id UNINDEXED,
                    content='summaries',
                    content_rowid='id'
                );
            """
            )
            
            conn.execute(
                """
                INSERT INTO summaries_fts(rowid, title, content, paper_id)
                SELECT id, COALESCE(title, ''), content, paper_id FROM summaries;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER summaries_ai AFTER INSERT ON summaries BEGIN
                    INSERT INTO summaries_fts(rowid, title, content, paper_id)
                    VALUES (new.id, COALESCE(new.title, ''), new.content, new.paper_id);
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER summaries_au AFTER UPDATE ON summaries BEGIN
                    UPDATE summaries_fts SET title=COALESCE(new.title, ''), content=new.content, paper_id=new.paper_id
                    WHERE rowid=old.id;
                END;
            """
            )
            
            conn.execute(
                """
                CREATE TRIGGER summaries_ad AFTER DELETE ON summaries BEGIN
                    DELETE FROM summaries_fts WHERE rowid=old.id;
                END;
            """
            )
        
        conn.commit()
