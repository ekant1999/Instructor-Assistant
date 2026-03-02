from __future__ import annotations

"""
Compatibility wrapper for YouTube transcript utilities.

Backend code now delegates to the reusable Phase 1 package (`ia_phase1`).
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.youtube_transcript import (  # noqa: E402
    download_youtube_transcript as _phase1_download_youtube_transcript,
    extract_youtube_video_id,
    is_youtube_url,
)


def _backend_default_transcript_dir() -> Path:
    configured = os.getenv("YOUTUBE_TRANSCRIPT_OUTPUT_DIR", "").strip()
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        root = (Path(__file__).resolve().parents[1] / "data" / "transcripts").expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def download_youtube_transcript(
    video_url: str,
    output_dir: Optional[Path] = None,
    preferred_langs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    target_dir = output_dir if output_dir is not None else _backend_default_transcript_dir()
    return _phase1_download_youtube_transcript(
        video_url=video_url,
        output_dir=target_dir,
        preferred_langs=preferred_langs,
    )


__all__ = [
    "extract_youtube_video_id",
    "is_youtube_url",
    "download_youtube_transcript",
]
