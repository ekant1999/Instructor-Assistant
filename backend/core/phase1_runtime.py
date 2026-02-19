from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def ensure_ia_phase1_on_path() -> Optional[Path]:
    """
    Ensure the local `modules/phase1-python/src` path is importable.

    Resolution order:
    1) IA_PHASE1_SRC env var (absolute or relative path to `.../src`)
    2) Repo-local default: <repo>/modules/phase1-python/src
    """
    configured = os.getenv("IA_PHASE1_SRC", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())

    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "modules" / "phase1-python" / "src")

    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.exists():
            continue
        value = str(resolved)
        if value not in sys.path:
            sys.path.insert(0, value)
        return resolved
    return None
