"""Shared utilities for qwen tools."""
from __future__ import annotations

import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
# Download location shared by all tools
DOWNLOADS_DIR = BACKEND_ROOT / "data" / "pdfs"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def safe_path(raw: str | Path, default_name: str = "output") -> Path:
    """
    Resolve a user-provided path, anchoring to the downloads directory unless the
    path is absolute and already inside the project root.
    """
    candidate = Path(raw) if isinstance(raw, (str, Path)) else Path(default_name)
    project_root = REPO_ROOT
    if candidate.is_absolute():
        try:
            candidate.relative_to(project_root)
            return candidate
        except ValueError:
            # Outside the repo; fall back to downloads dir
            return DOWNLOADS_DIR / candidate.name
    return DOWNLOADS_DIR / candidate


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)
