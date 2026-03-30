from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List

from .models import MarkdownRenderAudit

_HEADING_RE = re.compile(r"^(#{2,6})\s+(.*?)\s*$")
_CORE_HEADINGS = {
    "abstract",
    "introduction",
    "related work",
    "related works",
    "method",
    "methods",
    "methodology",
    "experiment",
    "experiments",
    "results",
    "conclusion",
    "conclusions",
    "discussion",
    "discussions",
    "appendix",
    "references",
}


def audit_rendered_markdown(markdown: str, *, metadata: Dict[str, Any]) -> MarkdownRenderAudit:
    headings: List[tuple[int, str, str]] = []
    for line in str(markdown or "").splitlines():
        match = _HEADING_RE.match(line.strip())
        if not match:
            continue
        title = str(match.group(2) or "").strip()
        if not title:
            continue
        headings.append((len(match.group(1)), title, _normalize_heading(title)))

    counts = Counter(normalized for _, _, normalized in headings if normalized)
    suspicious = [title for _, title, normalized in headings if _looks_like_suspicious_heading(title, normalized=normalized, metadata=metadata)]
    issues: List[str] = []

    page_count = _safe_int(metadata.get("page_count"), 0)
    total_headings = len(headings)
    max_reasonable_headings = max(24, page_count * 2 + 6) if page_count > 0 else 24
    if total_headings > max_reasonable_headings:
        issues.append(f"too many headings ({total_headings}) for page count {page_count or 'unknown'}")

    for normalized, count in sorted(counts.items()):
        if not normalized:
            continue
        if normalized in _CORE_HEADINGS and count > 1:
            issues.append(f"duplicate core heading '{normalized}' ({count})")
        elif count > 3:
            issues.append(f"heading repeated excessively '{normalized}' ({count})")

    if suspicious:
        issues.append(f"suspicious headings detected ({len(suspicious)})")

    return MarkdownRenderAudit(
        conservative_recommended=bool(issues),
        issue_count=len(issues),
        issues=issues,
        suspicious_headings=suspicious[:12],
        heading_counts=dict(sorted(counts.items())),
        total_headings=total_headings,
    )


def _normalize_heading(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^\d+(?:\.\d+)*[\)\.]?\s+", "", text)
    text = re.sub(r"^[A-Z](?:\.\d+)*[\)\.]?\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_suspicious_heading(title: str, *, normalized: str, metadata: Dict[str, Any]) -> bool:
    compact = " ".join(str(title or "").split()).strip()
    lowered = compact.lower()
    word_count = len(re.findall(r"[A-Za-z]{2,}", compact))
    title_norm = _normalize_heading(str(metadata.get("title") or ""))

    if not compact:
        return True
    if "{" in compact or "}" in compact:
        return True
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        return True
    if title_norm and normalized == title_norm:
        return True
    if re.search(r"\\[A-Za-z]+", compact):
        return True
    if compact.startswith(("Figure ", "Table ", "Fig. ", "Eq. ")):
        return True
    if _looks_like_equationish_heading(compact):
        return True
    if word_count > 14:
        return True
    if _looks_like_sentenceish_prose(compact) and word_count > 6:
        return True
    return False


def _looks_like_equationish_heading(text: str) -> bool:
    compact = " ".join(str(text or "").split()).strip()
    if not compact:
        return False
    if any(marker in compact for marker in ("$$", "\\begin", "\\end")):
        return True
    if re.search(r"[=<>^_]|\\[A-Za-z]+|\{|\}", compact):
        return True
    math_tokens = len(re.findall(r"[=+\-*/^_<>∥∑∫\\()\[\]{}]", compact))
    alpha_words = len(re.findall(r"[A-Za-z]{2,}", compact))
    return math_tokens >= 3 and alpha_words >= 2


def _looks_like_sentenceish_prose(text: str) -> bool:
    lowered = str(text or "").lower()
    if re.search(r"[.!?]\s", text):
        return True
    stopwords = re.findall(r"\b(the|and|that|with|from|this|these|our|their|which|while|using|without|into|through|because|however|although|where|when)\b", lowered)
    return len(stopwords) >= 3


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
