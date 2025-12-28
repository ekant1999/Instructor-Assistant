"""News fetching from Bing News RSS."""
from __future__ import annotations

import urllib.parse
from typing import Dict

import feedparser
import requests

from .utils import strip_html


def get_news(topic: str, limit: int = 10) -> Dict[str, object]:
    """
    Fetch from Bing News RSS - works like Google News but faster updates.
    Great for specific/niche topics.
    """
    encoded_topic = urllib.parse.quote(topic)
    url = f"https://www.bing.com/news/search?q={encoded_topic}&format=rss"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        
        articles = [
            {
                "title": strip_html(entry.get("title", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": strip_html(entry.get("summary", entry.get("description", "")))[:500],
                "source": entry.get("source", {}).get("title", "Unknown") if isinstance(entry.get("source"), dict) else "Bing News"
            }
            for entry in (feed.entries or [])[:limit]
        ]
        
        return {"topic": topic, "articles": articles}
    
    except Exception as e:
        print(f"Bing News fetch error: {e}")
        return {"topic": topic, "articles": []}

