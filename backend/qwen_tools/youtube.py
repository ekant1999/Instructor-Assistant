"""YouTube search and download tools."""
from __future__ import annotations

from typing import Dict, List, Optional

import yt_dlp

from .utils import safe_path


def youtube_search(query: str, max_results: int = 5) -> Dict[str, object]:
    """Search YouTube for videos."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    videos: List[Dict[str, object]] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        for entry in info.get("entries", []) or []:
            if not entry:
                continue
            videos.append(
                {
                    "title": entry.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    "duration": entry.get("duration", 0),
                    "channel": entry.get("channel", ""),
                    "view_count": entry.get("view_count", 0),
                }
            )
    return {"query": query, "videos": videos}


def youtube_download(video_url: str, output_path: Optional[str] = None) -> Dict[str, object]:
    """Download a YouTube video to the downloads directory."""
    out_template = safe_path(output_path or "%(title)s.%(ext)s")
    out_template.parent.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(out_template),
        "format": "best[ext=mp4]/best",
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)

    return {
        "video_url": video_url,
        "title": info.get("title", ""),
        "file_path": filename,
        "duration": info.get("duration", 0),
    }

