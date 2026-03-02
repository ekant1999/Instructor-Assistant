from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def query_tokens(query: str) -> List[str]:
    if not query:
        return []
    tokens = [t.lower() for t in _WORD_RE.findall(query) if len(t) > 2]
    return list(dict.fromkeys(tokens))


def lexical_hits(tokens: List[str], text: str) -> int:
    if not tokens or not text:
        return 0
    text_lower = text.lower()
    return sum(1 for token in tokens if token in text_lower)


def pgvector_score(row: Dict[str, Any]) -> float:
    for key in ("hybrid_score", "similarity", "score"):
        val = row.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return 0.0


def select_block_for_query(row: Dict[str, Any], tokens: List[str]) -> Dict[str, Any]:
    metadata = row.get("metadata")
    blocks = metadata.get("blocks") if isinstance(metadata, dict) else None
    if not blocks:
        section_canonical = ""
        if isinstance(metadata, dict):
            section_canonical = str(
                metadata.get("section_primary")
                or metadata.get("section_canonical")
                or ""
            ).strip()
        return {
            "page_no": row.get("page_no"),
            "block_index": row.get("block_index"),
            "bbox": row.get("bbox"),
            "text": row.get("text") or "",
            "lex_hits": lexical_hits(tokens, row.get("text") or ""),
            "section_canonical": section_canonical,
        }

    best_block: Optional[Dict[str, Any]] = None
    best_hits = -1
    best_len = -1
    for block in blocks:
        text = block.get("text") or ""
        hits = lexical_hits(tokens, text) if tokens else 0
        if hits > best_hits or (hits == best_hits and len(text) > best_len):
            best_block = block
            best_hits = hits
            best_len = len(text)

    if not best_block:
        section_canonical = ""
        if isinstance(metadata, dict):
            section_canonical = str(
                metadata.get("section_primary")
                or metadata.get("section_canonical")
                or ""
            ).strip()
        return {
            "page_no": row.get("page_no"),
            "block_index": row.get("block_index"),
            "bbox": row.get("bbox"),
            "text": row.get("text") or "",
            "lex_hits": lexical_hits(tokens, row.get("text") or ""),
            "section_canonical": section_canonical,
        }

    block_meta = best_block.get("metadata") if isinstance(best_block, dict) else None
    section_canonical = ""
    if isinstance(block_meta, dict):
        section_canonical = str(
            block_meta.get("section_canonical")
            or block_meta.get("section_primary")
            or ""
        ).strip()
    if not section_canonical and isinstance(metadata, dict):
        section_canonical = str(
            metadata.get("section_primary")
            or metadata.get("section_canonical")
            or ""
        ).strip()

    return {
        "page_no": best_block.get("page_no") or row.get("page_no"),
        "block_index": best_block.get("block_index") or row.get("block_index"),
        "bbox": best_block.get("bbox") or row.get("bbox"),
        "text": best_block.get("text") or row.get("text") or "",
        "lex_hits": best_hits,
        "section_canonical": section_canonical,
    }


def build_match_snippet(query: str, tokens: List[str], text: str, max_len: int = 240) -> str:
    if not text:
        return ""
    clean = " ".join(text.replace("\x00", "").split())
    if not clean:
        return ""
    if not tokens:
        return clean[:max_len]
    lower = clean.lower()
    target_tokens = [t for t in tokens if t in lower]
    if target_tokens:
        words = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_RE.finditer(clean)]
        target_set = set(target_tokens)
        needed = len(target_set)
        counts: Dict[str, int] = {}
        have = 0
        best_window: Optional[tuple[int, int]] = None
        left = 0
        for right, (token, _start, end) in enumerate(words):
            if token in target_set:
                counts[token] = counts.get(token, 0) + 1
                if counts[token] == 1:
                    have += 1
            while have == needed and left <= right:
                window_start = words[left][1]
                window_end = end
                if best_window is None or (window_end - window_start) < (best_window[1] - best_window[0]):
                    best_window = (window_start, window_end)
                left_token = words[left][0]
                if left_token in target_set:
                    counts[left_token] -= 1
                    if counts[left_token] == 0:
                        have -= 1
                left += 1
        if best_window:
            pad = 12
            start = max(0, best_window[0] - pad)
            end = min(len(clean), best_window[1] + pad)
            snippet = clean[start:end]
            if len(snippet) <= max_len:
                return snippet
            clean = snippet
            lower = clean.lower()

    tokens_sorted = sorted(tokens, key=len, reverse=True)
    anchor = -1
    for token in tokens_sorted:
        idx = lower.find(token)
        if idx != -1:
            anchor = idx
            break
    if anchor == -1:
        return clean[:max_len]
    target_len = min(max_len, max(60, len(query) * 2))
    start = max(0, anchor - target_len // 4)
    if start > 0:
        prior_space = clean.rfind(" ", 0, start)
        if prior_space != -1:
            start = prior_space + 1
    end = min(len(clean), start + target_len)
    if end < len(clean):
        next_space = clean.find(" ", end)
        if next_space != -1:
            end = next_space
    return clean[start:end]


__all__ = [
    "query_tokens",
    "lexical_hits",
    "pgvector_score",
    "select_block_for_query",
    "build_match_snippet",
]
