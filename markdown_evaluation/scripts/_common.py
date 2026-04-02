from __future__ import annotations

import contextlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MARKDOWN_EVAL_DIR = ROOT / "markdown_evaluation"
METADATA_PATH = MARKDOWN_EVAL_DIR / "metadata.jsonl"
GOLD_DIR = MARKDOWN_EVAL_DIR / "gold" / "docs"
OUTPUT_DIR = MARKDOWN_EVAL_DIR / "outputs"
NORMALIZED_DIR = MARKDOWN_EVAL_DIR / "normalized"
REPORT_DIR = MARKDOWN_EVAL_DIR / "reports"
RUN_DIR = MARKDOWN_EVAL_DIR / "runs"


@dataclass(slots=True)
class BenchmarkDoc:
    doc_id: str
    pdf_path: Path
    title: str = ""
    paper_id: Optional[int] = None
    layout_type: str = "unknown"
    doc_tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["pdf_path"] = str(self.pdf_path)
        return payload


def ensure_dirs() -> None:
    for path in (GOLD_DIR, OUTPUT_DIR, NORMALIZED_DIR, REPORT_DIR, RUN_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_metadata(path: Path = METADATA_PATH) -> List[BenchmarkDoc]:
    docs: List[BenchmarkDoc] = []
    for row in read_jsonl(path):
        pdf_path = Path(str(row["pdf_path"]))
        if not pdf_path.is_absolute():
            pdf_path = (ROOT / pdf_path).resolve()
        docs.append(
            BenchmarkDoc(
                doc_id=str(row["doc_id"]),
                pdf_path=pdf_path,
                title=str(row.get("title") or ""),
                paper_id=int(row["paper_id"]) if row.get("paper_id") is not None else None,
                layout_type=str(row.get("layout_type") or "unknown"),
                doc_tags=[str(tag) for tag in row.get("doc_tags") or []],
                source_url=str(row.get("source_url")) if row.get("source_url") else None,
                notes=str(row.get("notes") or ""),
            )
        )
    return docs


def select_docs(doc_ids: Optional[Sequence[str]] = None, *, path: Path = METADATA_PATH) -> List[BenchmarkDoc]:
    docs = load_metadata(path)
    if not doc_ids:
        return docs
    wanted = {str(doc_id).strip() for doc_id in doc_ids if str(doc_id).strip()}
    by_id = {doc.doc_id: doc for doc in docs}
    missing = sorted(wanted - set(by_id))
    if missing:
        raise KeyError(f"Unknown doc_id(s): {', '.join(missing)}")
    return [by_id[doc_id] for doc_id in doc_ids if str(doc_id).strip() in by_id]


def system_root(system: str) -> Path:
    return OUTPUT_DIR / system


def system_doc_dir(system: str, doc_id: str) -> Path:
    return system_root(system) / "docs" / doc_id


def normalized_doc_path(system: str, doc_id: str) -> Path:
    return NORMALIZED_DIR / system / f"{doc_id}.json"


def gold_doc_path(doc_id: str) -> Path:
    return GOLD_DIR / f"{doc_id}.json"


def load_gold_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    path = gold_doc_path(doc_id)
    if not path.exists():
        return None
    return read_json(path)


@contextlib.contextmanager
def temporary_environ(updates: Dict[str, Optional[str]]) -> Iterator[None]:
    previous: Dict[str, Optional[str]] = {}
    try:
        for key, value in updates.items():
            previous[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


_TEXT_NORMALIZE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def collapse_ws(text: str) -> str:
    return _TEXT_NORMALIZE_RE.sub(" ", str(text or "")).strip()


def normalize_match_text(text: str) -> str:
    collapsed = collapse_ws(text).lower()
    collapsed = _NON_ALNUM_RE.sub(" ", collapsed)
    return collapse_ws(collapsed)


def slugify(text: str) -> str:
    return normalize_match_text(text).replace(" ", "_") or "item"


def derive_stable_paper_id(pdf_path: Path) -> int:
    import hashlib

    hasher = hashlib.blake2b(digest_size=8)
    with pdf_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    raw = int.from_bytes(hasher.digest(), "big")
    return 100_000_000_000 + (raw % 900_000_000_000)
