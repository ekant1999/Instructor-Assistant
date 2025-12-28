"""Web search tools using SearXNG and DuckDuckGo."""
from __future__ import annotations

import os
import time
from typing import Dict, Optional

import requests
from duckduckgo_search import DDGS

try:
    from duckduckgo_search.exceptions import RatelimitException
except Exception:  # pragma: no cover
    RatelimitException = Exception


def _searxng_search(query: str, max_results: int) -> tuple[Optional[Dict[str, object]], Optional[str]]:
    """
    Optional fallback search using SearXNG public/self-hosted instance.
    Returns (result, error_message).
    """
    instance_url = os.getenv("SEARXNG_URL") or ""
    if not instance_url:
        public_instances = [
            "https://searx.be",
            "https://search.sapti.me",
            "https://searx.tiekoetter.com",
            "https://search.bus-hit.me",
            "https://searx.work",
        ]
        instance_url = public_instances[0]
    try:
        url = instance_url.rstrip("/") + "/search"
        params = {"q": query, "format": "json", "pageno": 1}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "engine": item.get("engine", "unknown"),
                }
            )
        return {"query": query, "results": results, "source": "searxng"}, None
    except Exception as exc:
        return None, str(exc)


def web_search(query: str, max_results: int = 5) -> Dict[str, object]:
    """Search the web. Prefer SearXNG; fall back to DuckDuckGo."""
    capped_max = max(1, min(max_results or 5, 10))
    # Try SearXNG first (self-hosted or public)
    searx_results, searx_error = _searxng_search(query, capped_max)
    if searx_results is not None:
        return searx_results

    # Fallback to DuckDuckGo
    time.sleep(0.6)
    with DDGS() as ddgs:
        try:
            results = list(ddgs.text(query, max_results=capped_max))
            return {
                "query": query,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                    for r in results
                ],
                "source": "duckduckgo",
            }
        except Exception as exc:
            detail = f"DuckDuckGo search failed: {exc}"
            if searx_error:
                detail += f" | SearxNG fallback error: {searx_error}"
            raise ValueError(detail) from exc

