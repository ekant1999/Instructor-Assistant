from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .document_model import DocumentModel

_NORMALIZE_RE = re.compile(r"[^A-Za-z0-9]+")
_OCR_PLACEHOLDER_RE = re.compile(r"\[(?:ocr\s+unavailable|ocr\s+failed)[^\]]*\]|ocr\s+backend\s+not\s+configured", re.I)
_NOISE_HEADING_PREFIX_RE = re.compile(r"^(?:figure|fig\.?|table|algorithm|source|note|notes)\b", re.I)


@dataclass(slots=True)
class MarkdownQualityAudit:
    issues: List[str] = field(default_factory=list)
    duplicate_headings: List[str] = field(default_factory=list)
    suspicious_headings: List[str] = field(default_factory=list)
    empty_section_count: int = 0
    consecutive_empty_heading_runs: int = 0
    unresolved_ocr_placeholders: int = 0
    needs_conservative_fallback: bool = False


def _normalize_heading(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip().lower()
    cleaned = _NORMALIZE_RE.sub(" ", cleaned).strip()
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_suspicious_heading(title: str) -> bool:
    stripped = " ".join(str(title or "").split()).strip()
    if not stripped:
        return True
    words = stripped.split()
    if len(words) > 18:
        return True
    if _NOISE_HEADING_PREFIX_RE.match(stripped):
        return True
    if len(words) >= 8 and re.search(r"[.!?;,]$", stripped):
        return True
    first_alpha = next((ch for ch in stripped if ch.isalpha()), "")
    if first_alpha and first_alpha.islower():
        return True
    return False


def _count_ocr_placeholders(model: DocumentModel) -> int:
    count = 0
    for block in model.front_matter:
        if _OCR_PLACEHOLDER_RE.search(block.text or ""):
            count += 1
    for section in model.sections:
        if _OCR_PLACEHOLDER_RE.search(section.title or ""):
            count += 1
        for block in section.blocks:
            if _OCR_PLACEHOLDER_RE.search(block.text or ""):
                count += 1
    return count


def audit_document_model(model: DocumentModel) -> MarkdownQualityAudit:
    audit = MarkdownQualityAudit()
    heading_counts: Dict[str, int] = {}
    current_empty_run = 0

    for section in model.sections:
        heading_norm = _normalize_heading(section.title)
        if heading_norm:
            heading_counts[heading_norm] = heading_counts.get(heading_norm, 0) + 1
            if heading_counts[heading_norm] == 2:
                audit.duplicate_headings.append(section.title)

        if _is_suspicious_heading(section.title):
            audit.suspicious_headings.append(section.title)

        if not section.has_renderable_content():
            audit.empty_section_count += 1
            current_empty_run += 1
            audit.consecutive_empty_heading_runs = max(
                audit.consecutive_empty_heading_runs,
                current_empty_run,
            )
        else:
            current_empty_run = 0

    audit.unresolved_ocr_placeholders = _count_ocr_placeholders(model)

    if audit.duplicate_headings:
        audit.issues.append(f"duplicate_headings:{len(audit.duplicate_headings)}")
    if audit.suspicious_headings:
        audit.issues.append(f"suspicious_headings:{len(audit.suspicious_headings)}")
    if audit.empty_section_count:
        audit.issues.append(f"empty_sections:{audit.empty_section_count}")
    if audit.consecutive_empty_heading_runs >= 2:
        audit.issues.append(f"empty_heading_run:{audit.consecutive_empty_heading_runs}")
    if audit.unresolved_ocr_placeholders:
        audit.issues.append(f"ocr_placeholders:{audit.unresolved_ocr_placeholders}")

    section_count = max(len(model.sections), 1)
    audit.needs_conservative_fallback = (
        audit.consecutive_empty_heading_runs >= 3
        or audit.empty_section_count >= max(4, section_count // 3)
        or len(audit.duplicate_headings) >= 2
        or len(audit.suspicious_headings) >= 3
        or audit.unresolved_ocr_placeholders > 0
    )
    return audit
