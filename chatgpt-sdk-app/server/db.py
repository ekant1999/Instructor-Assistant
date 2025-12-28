"""
Minimal code to keep existing imports working.
Database logic shifted in backend.core.database.
"""
from backend.core.database import DB_PATH, get_conn, init_db, ensure_question_tables  # noqa: F401
