from __future__ import annotations

import copy
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Hashable, Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
VERSION_FILE = DATA_DIR / "search_index_version.txt"


def _read_int(path: Path, default: int = 0) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip() or default)
    except Exception:
        return default


def current_search_index_version() -> int:
    if not VERSION_FILE.exists():
        VERSION_FILE.write_text("0\n", encoding="utf-8")
        return 0
    return _read_int(VERSION_FILE, default=0)


_version_lock = threading.RLock()


def bump_search_index_version(reason: str = "") -> int:
    with _version_lock:
        version = current_search_index_version() + 1
        VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")
        return version


def normalize_search_query(query: str) -> str:
    return " ".join((query or "").split())


class _TTLCache:
    def __init__(self, *, maxsize: int, ttl_seconds: float):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._data: "OrderedDict[Hashable, tuple[float, Any]]" = OrderedDict()

    def _purge_expired(self, now: float) -> None:
        expired = [key for key, (expires_at, _) in self._data.items() if expires_at <= now]
        for key in expired:
            self._data.pop(key, None)

    def get(self, key: Hashable) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            self._purge_expired(now)
            payload = self._data.get(key)
            if payload is None:
                return None
            expires_at, value = payload
            if expires_at <= now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return copy.deepcopy(value)

    def set(self, key: Hashable, value: Any) -> None:
        now = time.monotonic()
        expires_at = now + self.ttl_seconds
        with self._lock:
            self._purge_expired(now)
            self._data[key] = (expires_at, copy.deepcopy(value))
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_paper_search_cache = _TTLCache(
    maxsize=int(os.getenv("PAPER_SEARCH_CACHE_SIZE", "256")),
    ttl_seconds=float(os.getenv("PAPER_SEARCH_CACHE_TTL_SECONDS", "300")),
)
_section_search_cache = _TTLCache(
    maxsize=int(os.getenv("SECTION_SEARCH_CACHE_SIZE", "512")),
    ttl_seconds=float(os.getenv("SECTION_SEARCH_CACHE_TTL_SECONDS", "300")),
)


def get_cached_paper_search(key: Hashable) -> Optional[Any]:
    return _paper_search_cache.get(key)


def set_cached_paper_search(key: Hashable, value: Any) -> None:
    _paper_search_cache.set(key, value)


def get_cached_section_search(key: Hashable) -> Optional[Any]:
    return _section_search_cache.get(key)


def set_cached_section_search(key: Hashable, value: Any) -> None:
    _section_search_cache.set(key, value)


def clear_search_caches() -> None:
    _paper_search_cache.clear()
    _section_search_cache.clear()
