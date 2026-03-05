from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_DASH_NORMALIZE_RE = re.compile(r"[‐‑‒–—―-]+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


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


def _normalize_loose_text(value: str) -> str:
    if not value:
        return ""
    text = value.lower()
    text = _DASH_NORMALIZE_RE.sub("-", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return " ".join(text.split())


def _ordered_token_coverage(tokens: List[str], normalized_text: str) -> float:
    if not tokens or not normalized_text:
        return 0.0
    pos = 0
    matched = 0
    for token in tokens:
        idx = normalized_text.find(token, pos)
        if idx == -1:
            continue
        matched += 1
        pos = idx + len(token)
    return matched / max(1, len(tokens))


def _query_match_score(query: str, tokens: List[str], text: str) -> Dict[str, Any]:
    token_hits = lexical_hits(tokens, text)
    if not text:
        return {"score": 0.0, "lex_hits": token_hits, "exact_phrase": False}

    normalized_text = _normalize_loose_text(text)
    normalized_query = _normalize_loose_text(query)
    exact_phrase = bool(normalized_query and normalized_query in normalized_text)

    token_ratio = (token_hits / len(tokens)) if tokens else 0.0
    ordered_ratio = _ordered_token_coverage(tokens, normalized_text)

    bigram_hits = 0
    if len(tokens) >= 2:
        for idx in range(len(tokens) - 1):
            if f"{tokens[idx]} {tokens[idx + 1]}" in normalized_text:
                bigram_hits += 1

    score = (token_hits * 1.25) + (token_ratio * 1.1) + (ordered_ratio * 1.4) + (bigram_hits * 0.8)
    if exact_phrase:
        score += 8.0
    elif normalized_query and len(normalized_query) >= 20 and normalized_text:
        short_text = normalized_text[: max(260, len(normalized_query) * 2)]
        similarity = SequenceMatcher(None, normalized_query, short_text).ratio()
        if similarity >= 0.55:
            score += (similarity - 0.5) * 2.0

    return {
        "score": score,
        "lex_hits": token_hits,
        "exact_phrase": exact_phrase,
    }


def _coalesce_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


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


def select_block_for_query(row: Dict[str, Any], tokens: List[str], query: str = "") -> Dict[str, Any]:
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
        fallback_eval = _query_match_score(query, tokens, row.get("text") or "")
        return {
            "page_no": row.get("page_no"),
            "block_index": row.get("block_index"),
            "bbox": row.get("bbox"),
            "text": row.get("text") or "",
            "lex_hits": lexical_hits(tokens, row.get("text") or ""),
            "match_score": fallback_eval.get("score", 0.0),
            "exact_phrase": fallback_eval.get("exact_phrase", False),
            "section_canonical": section_canonical,
        }

    best_block: Optional[Dict[str, Any]] = None
    best_match_score = -1.0
    best_hits = -1
    best_len = -1
    best_exact_phrase = False
    for block in blocks:
        text = block.get("text") or ""
        match_eval = _query_match_score(query, tokens, text)
        match_score = float(match_eval.get("score", 0.0))
        hits = int(match_eval.get("lex_hits", 0))
        exact_phrase = bool(match_eval.get("exact_phrase", False))
        if (
            match_score > best_match_score
            or (match_score == best_match_score and exact_phrase and not best_exact_phrase)
            or (match_score == best_match_score and exact_phrase == best_exact_phrase and hits > best_hits)
            or (
                match_score == best_match_score
                and hits == best_hits
                and len(text) > best_len
            )
        ):
            best_block = block
            best_match_score = match_score
            best_hits = hits
            best_len = len(text)
            best_exact_phrase = exact_phrase

    if not best_block:
        section_canonical = ""
        if isinstance(metadata, dict):
            section_canonical = str(
                metadata.get("section_primary")
                or metadata.get("section_canonical")
                or ""
            ).strip()
        fallback_eval = _query_match_score(query, tokens, row.get("text") or "")
        return {
            "page_no": row.get("page_no"),
            "block_index": row.get("block_index"),
            "bbox": row.get("bbox"),
            "text": row.get("text") or "",
            "lex_hits": lexical_hits(tokens, row.get("text") or ""),
            "match_score": fallback_eval.get("score", 0.0),
            "exact_phrase": fallback_eval.get("exact_phrase", False),
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
        "page_no": _coalesce_not_none(best_block.get("page_no"), row.get("page_no")),
        "block_index": _coalesce_not_none(best_block.get("block_index"), row.get("block_index")),
        "bbox": _coalesce_not_none(best_block.get("bbox"), row.get("bbox")),
        "text": best_block.get("text") or row.get("text") or "",
        "lex_hits": best_hits,
        "match_score": best_match_score,
        "exact_phrase": best_exact_phrase,
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
