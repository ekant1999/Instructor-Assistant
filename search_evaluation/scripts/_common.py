from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEARCH_EVAL_DIR = ROOT / "search_evaluation"
PDF_DIR = SEARCH_EVAL_DIR / "pdfs"
REVIEW_DIR = SEARCH_EVAL_DIR / "reviews"
REPORT_DIR = SEARCH_EVAL_DIR / "reports"
RUN_DIR = SEARCH_EVAL_DIR / "runs"
STATE_DIR = SEARCH_EVAL_DIR / "state"
SCRIPT_DIR = SEARCH_EVAL_DIR / "scripts"
METADATA_PATH = SEARCH_EVAL_DIR / "metadata.jsonl"
QUERIES_PATH = SEARCH_EVAL_DIR / "queries.jsonl"
GOLD_PATH = SEARCH_EVAL_DIR / "gold.jsonl"
EVAL_DB_PATH = STATE_DIR / "app_eval.db"
IMPORT_MANIFEST_PATH = STATE_DIR / "import_manifest.json"

EVAL_PAPER_ID_START = 910001


def ensure_dirs() -> None:
    for path in (PDF_DIR, REVIEW_DIR, REPORT_DIR, RUN_DIR, STATE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def get_eval_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(EVAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def eval_conn_factory() -> Iterator[sqlite3.Connection]:
    conn = get_eval_conn()
    try:
        yield conn
    finally:
        conn.close()


def normalize_query_id(query: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in query.strip())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe[:80] or "query"


def truthy_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
