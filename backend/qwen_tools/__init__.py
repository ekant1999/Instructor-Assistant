"""Qwen tools package - Tool registry and dispatcher."""
from __future__ import annotations

from typing import Dict

from .arxiv import arxiv_download, arxiv_search
from .news import get_news
from .pdf import pdf_summary
from .web_search import web_search
from .youtube import youtube_download, youtube_search

# Tool registry - follows Open/Closed Principle
TOOL_MAP: Dict[str, callable] = {
    "web_search": web_search,
    "get_news": get_news,
    "arxiv_search": arxiv_search,
    "arxiv_download": arxiv_download,
    "pdf_summary": pdf_summary,
    "youtube_search": youtube_search,
    "youtube_download": youtube_download,
}


def execute_tool(name: str, **kwargs) -> Dict[str, object]:
    """Dispatch tool by name; raises if unknown or underlying tool fails."""
    if name not in TOOL_MAP:
        raise ValueError(f"Unknown tool: {name}")
    return TOOL_MAP[name](**kwargs)


# Export all functions for backward compatibility
__all__ = [
    "execute_tool",
    "web_search",
    "get_news",
    "arxiv_search",
    "arxiv_download",
    "pdf_summary",
    "youtube_search",
    "youtube_download",
    "TOOL_MAP",
]

