from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .document_model import DocumentBlock, DocumentModel, DocumentOutlineEntry, DocumentSection
from .quality import MarkdownQualityAudit, audit_document_model

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_PAGE_MODE_RE = re.compile(r"^<!--\s*page\s+(?P<page>\d+)\s+mode:\s*(?P<mode>[^>]+?)\s*-->\s*$", re.I)
_OCR_PAGE_RE = re.compile(r"^<!--\s*OCR\s+page\s+(?P<page>\d+)\s*-->\s*$", re.I)
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$")
_ARXIV_STAMP_RE = re.compile(r"^arxiv:\d{4}\.\d{4,5}v\d+\s+\[[^\]]+\]\s+\d{1,2}\s+\w+\s+\d{4}$", re.I)
_NUMBERED_PREFIX_RE = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3})*|[IVXLCDM]+|[A-Z])[\.\)]?\s+")
_VISIBLE_NUMBERED_PREFIX_RE = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3})*|[IVXLCDM]{2,})[\.\)]?\s+")
_SPLIT_CAPITAL_TOKEN_RE = re.compile(r"\b([A-Z])\s+([A-Z][A-Z][A-Z0-9-]*)\b")
_GLUED_APPENDIX_PREFIX_RE = re.compile(r"^([A-Z])([A-Z][A-Z0-9-]{2,})(\b.*)$")
_RUNNING_AUTHOR_HEADER_RE = re.compile(r"^[A-Z][A-Za-zÀ-ÖØ-öø-ÿ .,'-]{0,80}\bet\s+al\.?$", re.I)
_REFERENCE_ENTRY_HEADING_RE = re.compile(
    r"^[A-Z][A-Za-zÀ-ÖØ-öø-ÿ .,'-]{0,80},\s+.*(?:“|\"|').+",
)
_COMMON_TITLE_RE = re.compile(
    r"^(abstract|introduction|background|related\s+work[s]?|preliminar(?:y|ies)|method(?:s|ology)?|"
    r"approach|experiments?|results?|discussion|conclusion[s]?|references?|appendix|"
    r"limitations?|acknowledg(?:e)?ments?|implementation\s+details?|dataset[s]?|"
    r"prompt\s+templates?|ethical\s+consideration[s]?)\.?$",
    re.I,
)
_NUMBERED_HEADING_RE = re.compile(
    r"^(?:(?:\d{1,3}(?:\.\d{1,3})*)|(?:[IVXLCDM]{1,8})|(?:[A-Z]))[\.\)]?\s+[A-Z][^\n]{1,220}$",
)
_SECTION_HEADING_RE = re.compile(r"^Section\s+\d{1,3}\s*:\s+[A-Za-z][^\n]{1,220}$", re.I)
_PART_HEADING_RE = re.compile(r"^Part\s+\d{1,3}\s*:\s+[A-Za-z][^\n]{1,220}$", re.I)
_NOISE_HEADING_PREFIX_RE = re.compile(r"^(?:figure|fig\.?|table|algorithm|source|note|notes)\b", re.I)
_ASSET_ONLY_RE = re.compile(r"^\s*(?:!\[[^\]]*\]\([^)]*\)|\*\*Table\s+\d+.*\*\*)\s*$", re.I)
_ABSTRACT_INLINE_RE = re.compile(r"^(?P<title>abstract)\s*[—:-]\s*(?P<body>.+\S)\s*$", re.I)
_MEASUREMENT_FRAGMENT_RE = re.compile(
    r"^(?:ghz|mhz|khz|hz|fps|ms|gb|mb|kb|w|kw|v|ma|cm|mm|nm)\b",
    re.I,
)
_PRONOUN_SENTENCE_HEADING_RE = re.compile(
    r"^(?:we|this|these|those|our|it|they|there|here)\s+[a-z][a-z'-]*\b",
    re.I,
)
_MATH_SYMBOL_RE = re.compile(r"[∑∏∫√≤≥≠≈∞∂∇∈∉⊂⊆⊕⊗±×÷πθτγλμσϵϕψωαβδΔΦΨΩ→←↔·∙]")
_INLINE_MATH_TOKEN_RE = re.compile(
    r"(?:\\[A-Za-z]+|[A-Za-z]\w*\s*=\s*[^=]|[A-Za-z]\w*\([^)]*\)|[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9]+|"
    r"\d+\s*[+\-*/^=<>]\s*\d+|[+\-*/^=<>]{2,})"
)
_CODE_PREFIX_RE = re.compile(
    r"^(?:Algorithm\s+\d+|Input:|Output:|Require:|Ensure:|"
    r"for\b|while\b|if\b|else\b|elif\b|return\b|end\b|def\b|class\b|import\b|from\b|"
    r"//|#include\b|[A-Za-z_]\w*\s*\([^)]*\)\s*[:{]?)"
)
_ENUM_CODE_LINE_RE = re.compile(r"^\d{1,3}:\s*(?:\S.*)?$")
_REFERENCE_INITIAL_HEADING_RE = re.compile(r"^[A-Z][\.\)]\s+(.+)$")
_ALGORITHM_HEADER_RE = re.compile(r"^Algorithm\s+\d+\b", re.I)
_ALGORITHM_STEP_RE = re.compile(
    r"^(?:Initialize|Sample|Generate|Query|Compute|Estimate|Update|Set|"
    r"Collect|Store|Select|Obtain|Construct|Append|Train|Evaluate|Normalize|"
    r"Repeat|Return)\b"
)
_ALGORITHM_END_RE = re.compile(r"^(?:\d{1,3}:\s*)?end(?:\s+(?:for|while|if|do))?\s*$", re.I)


def _repair_glued_appendix_prefix(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if _COMMON_TITLE_RE.match(cleaned):
        return cleaned
    match = _GLUED_APPENDIX_PREFIX_RE.match(cleaned)
    if not match:
        return cleaned
    prefix, title, rest = match.groups()
    if prefix not in {"A", "B", "C", "D", "E", "F", "G", "H", "I"}:
        return cleaned
    if not re.search(r"[aeiou]", title, re.I):
        return cleaned
    return f"{prefix} {title}{rest}".strip()


def normalize_heading_title(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    cleaned = cleaned.rstrip("# ").strip()
    cleaned = re.sub(r"^[*_`]+|[*_`]+$", "", cleaned)
    while True:
        repaired = _SPLIT_CAPITAL_TOKEN_RE.sub(r"\1\2", cleaned)
        if repaired == cleaned:
            break
        cleaned = repaired
    cleaned = _repair_glued_appendix_prefix(cleaned)
    cleaned = _NUMBERED_PREFIX_RE.sub("", cleaned).strip(" .:-")
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", cleaned).strip().lower()
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_heading_title(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    cleaned = cleaned.rstrip("# ").strip()
    cleaned = re.sub(r"^[*_`]+|[*_`]+$", "", cleaned)
    while True:
        repaired = _SPLIT_CAPITAL_TOKEN_RE.sub(r"\1\2", cleaned)
        if repaired == cleaned:
            break
        cleaned = repaired
    cleaned = _repair_glued_appendix_prefix(cleaned)
    cleaned = _VISIBLE_NUMBERED_PREFIX_RE.sub("", cleaned).strip(" .:-")
    return cleaned


def _heading_level_from_plain_text(line: str) -> int:
    stripped = line.strip()
    if _PART_HEADING_RE.match(stripped) or _SECTION_HEADING_RE.match(stripped) or _COMMON_TITLE_RE.match(stripped):
        return 2
    match = re.match(r"^(\d{1,3}(?:\.\d{1,3})*)[\.\)]?\s+", stripped)
    if match:
        depth = match.group(1).count(".") + 1
        return min(2 + max(depth - 1, 0), 6)
    if re.match(r"^[IVXLCDM]+[\.\)]?\s+", stripped, re.I):
        return 2
    if re.match(r"^[A-Z][\.\)]?\s+", stripped):
        return 3
    return 2


def _build_outline_lookup(
    outline_entries: Optional[List[DocumentOutlineEntry]],
) -> Dict[str, List[DocumentOutlineEntry]]:
    lookup: Dict[str, List[DocumentOutlineEntry]] = {}
    for entry in outline_entries or []:
        norm = normalize_heading_title(entry.title)
        if not norm:
            continue
        lookup.setdefault(norm, []).append(entry)
    return lookup


def _resolve_outline_entry(
    title: str,
    *,
    current_page: int,
    outline_lookup: Dict[str, List[DocumentOutlineEntry]],
) -> Optional[DocumentOutlineEntry]:
    norm = normalize_heading_title(title)
    candidates = outline_lookup.get(norm, [])
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda entry: (
            abs((entry.page_num or current_page) - current_page),
            max(entry.level, 1),
        ),
    )


def _looks_like_sentence_heading_noise(text: str) -> bool:
    stripped = " ".join(str(text or "").split()).strip()
    if not stripped:
        return True
    words = stripped.split()
    if len(words) >= 4 and _PRONOUN_SENTENCE_HEADING_RE.match(stripped):
        return True
    if len(words) > 16:
        return True
    if len(words) >= 8 and re.search(r"[.!?;,]$", stripped):
        return True
    if len(words) >= 8:
        lowercaseish = 0
        alpha_words = 0
        for word in words:
            letters = [ch for ch in word if ch.isalpha()]
            if not letters:
                continue
            alpha_words += 1
            if letters[0].islower() or word.lower() in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
                lowercaseish += 1
        if alpha_words >= 8 and lowercaseish / max(alpha_words, 1) >= 0.6:
            return True
    return False


def _extract_inline_heading_and_body(line: str, *, title_hint: str) -> Optional[Tuple[int, str, str]]:
    stripped = " ".join(str(line or "").split()).strip()
    if not stripped:
        return None
    abstract_match = _ABSTRACT_INLINE_RE.match(stripped)
    if not abstract_match:
        return None
    title = clean_heading_title(abstract_match.group("title"))
    body = abstract_match.group("body").strip()
    if not title or _is_doc_title_noise(title, title_hint=title_hint):
        return None
    return 2, title, body


def _is_doc_title_noise(title: str, *, title_hint: str) -> bool:
    normalized = normalize_heading_title(title)
    hint = normalize_heading_title(title_hint)
    if not normalized:
        return True
    if hint and normalized == hint:
        return True
    if re.fullmatch(r"[a-z]\d{3}", normalized):
        return True
    if _ARXIV_STAMP_RE.match(" ".join(str(title or "").split())):
        return True
    if _RUNNING_AUTHOR_HEADER_RE.match(" ".join(str(title or "").split())):
        return True
    return False


def _can_start_body_sections(title: str) -> bool:
    stripped = " ".join(str(title or "").split()).strip()
    stripped = re.sub(r"^#{1,6}\s+", "", stripped).strip()
    normalized = normalize_heading_title(stripped)
    if not normalized:
        return False
    if _COMMON_TITLE_RE.match(stripped):
        return True
    if _SECTION_HEADING_RE.match(stripped) or _PART_HEADING_RE.match(stripped):
        return True
    if re.match(r"^(?:\d{1,3}(?:\.\d{1,3})*|[IVXLCDM]+)[\.\)]?\s+", stripped, re.I):
        return True
    return False


def _looks_like_reference_entry_heading(title: str) -> bool:
    stripped = " ".join(str(title or "").split()).strip()
    if not stripped:
        return False
    if _REFERENCE_ENTRY_HEADING_RE.match(stripped):
        return True
    return "," in stripped and "et al" in stripped.lower() and len(stripped.split()) >= 4


def _looks_like_reference_continuation_heading(title: str) -> bool:
    stripped = " ".join(str(title or "").split()).strip()
    match = _REFERENCE_INITIAL_HEADING_RE.match(stripped)
    if not match:
        return False
    rest = match.group(1).strip()
    words = rest.split()
    if not words:
        return False
    if "," in rest:
        return True
    if len(words) >= 4 and re.search(r"[.!?]", rest):
        return True
    if len(words) >= 4:
        alpha_words = 0
        lowercaseish = 0
        for word in words:
            letters = [ch for ch in word if ch.isalpha()]
            if not letters:
                continue
            alpha_words += 1
            if letters[0].islower() or word.lower() in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
                lowercaseish += 1
        if alpha_words >= 4 and lowercaseish / max(alpha_words, 1) >= 0.4:
            return True
    return False


def _looks_like_code_line(text: str) -> bool:
    stripped = str(text or "").rstrip()
    compact = stripped.strip()
    if not compact:
        return False
    if compact.startswith("```"):
        return False
    if _ENUM_CODE_LINE_RE.match(compact):
        return True
    if _CODE_PREFIX_RE.match(compact):
        return True
    if compact.endswith(";") and re.search(r"[=(){}[\]]", compact) and " " not in compact.split(";", 1)[0]:
        return True
    leading_spaces = len(stripped) - len(stripped.lstrip(" "))
    if leading_spaces >= 4 and re.search(r"[=(){}[\]:]", compact):
        return True
    return False


def _looks_like_algorithm_context_line(text: str) -> bool:
    stripped = " ".join(str(text or "").split()).strip()
    if not stripped:
        return False
    if _ALGORITHM_STEP_RE.match(stripped):
        return True
    if _ENUM_CODE_LINE_RE.match(stripped):
        return True
    if _looks_like_code_line(stripped):
        return True
    return False


def _is_algorithm_terminal_line(text: str) -> bool:
    stripped = " ".join(str(text or "").split()).strip()
    if not stripped:
        return False
    return bool(_ALGORITHM_END_RE.match(stripped))


def _looks_like_math_line(text: str) -> bool:
    stripped = " ".join(str(text or "").split()).strip()
    if not stripped:
        return False
    if stripped.startswith("```") or _ASSET_ONLY_RE.match(stripped):
        return False
    if _PAGE_MODE_RE.match(stripped) or _OCR_PAGE_RE.match(stripped):
        return False
    if re.search(r"https?://|www\.", stripped, re.I):
        return False
    if re.fullmatch(r"\(\d{1,3}[a-z]?\)", stripped):
        return True
    if len(stripped) > 220:
        return False

    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", stripped)
    math_hits = len(_MATH_SYMBOL_RE.findall(stripped))
    has_inline_math = bool(_INLINE_MATH_TOKEN_RE.search(stripped))
    has_operator = bool(re.search(r"[=<>]|[+\-*/^]{1,2}", stripped))
    symbol_count = sum(1 for ch in stripped if not ch.isalnum() and not ch.isspace())
    symbol_ratio = symbol_count / max(len(stripped), 1)

    if math_hits >= 2 and len(words) <= 20:
        return True
    if has_inline_math and has_operator and len(words) <= 18 and symbol_ratio >= 0.12:
        return True
    if symbol_ratio >= 0.35 and len(words) <= 10 and has_operator:
        return True
    return False


def _classify_body_block_kind(
    text: str,
    *,
    current_section_norm: str,
    algorithm_context_active: bool = False,
) -> str:
    stripped = str(text or "").strip()
    if _ASSET_ONLY_RE.match(stripped):
        return "asset"
    if current_section_norm != "references":
        if _looks_like_code_line(text):
            return "code"
        if algorithm_context_active and (
            _looks_like_algorithm_context_line(text) or _looks_like_math_line(text)
        ):
            return "code"
        if _looks_like_math_line(text):
            return "math"
    return "text"


def _looks_like_inline_title_fragment(title: str) -> bool:
    stripped = " ".join(str(title or "").split()).strip()
    if not stripped:
        return False
    if _COMMON_TITLE_RE.match(stripped) or _SECTION_HEADING_RE.match(stripped) or _PART_HEADING_RE.match(stripped):
        return False
    if _NUMBERED_HEADING_RE.match(stripped):
        return False
    words = stripped.split()
    if 2 <= len(words) <= 10 and stripped.upper() == stripped:
        return False
    if ":" in stripped and len(words) >= 4:
        return True
    return len(words) >= 8


def _looks_like_outline_title_block(text: str) -> bool:
    stripped = " ".join(str(text or "").split()).strip()
    if not stripped:
        return False
    if _HEADING_RE.match(stripped) or _ASSET_ONLY_RE.match(stripped):
        return False
    if _PAGE_MODE_RE.match(stripped) or _OCR_PAGE_RE.match(stripped):
        return False
    if _PAGE_NUM_RE.fullmatch(stripped):
        return False
    if len(stripped.split()) > 16:
        return False
    return not _looks_like_sentence_heading_noise(stripped)


def _extract_heading(
    line: str,
    *,
    title_hint: str,
    current_page: int,
    current_section_norm: str,
    outline_lookup: Dict[str, List[DocumentOutlineEntry]],
) -> Optional[Tuple[int, str]]:
    stripped = line.strip()
    if not stripped:
        return None
    if _PAGE_MODE_RE.match(stripped) or _OCR_PAGE_RE.match(stripped):
        return None
    if _ASSET_ONLY_RE.match(stripped):
        return None
    if _looks_like_reference_entry_heading(stripped):
        return None
    if current_section_norm == "references" and _looks_like_reference_continuation_heading(stripped):
        return None

    match = _HEADING_RE.match(stripped)
    if match:
        level = len(match.group(1))
        raw_title = match.group(2)
        title = clean_heading_title(match.group(2))
    else:
        if not (_COMMON_TITLE_RE.match(stripped) or _NUMBERED_HEADING_RE.match(stripped) or _SECTION_HEADING_RE.match(stripped) or _PART_HEADING_RE.match(stripped)):
            return None
        if _looks_like_sentence_heading_noise(stripped):
            return None
        level = _heading_level_from_plain_text(stripped)
        raw_title = stripped
        title = clean_heading_title(stripped)

    if not title:
        return None
    if _MEASUREMENT_FRAGMENT_RE.match(title):
        return None
    first_alpha = next((ch for ch in title if ch.isalpha()), "")
    if (
        first_alpha
        and first_alpha.islower()
        and not _COMMON_TITLE_RE.match(title)
        and not _SECTION_HEADING_RE.match(title)
        and not _PART_HEADING_RE.match(title)
        and not _NUMBERED_HEADING_RE.match(title)
    ):
        return None
    if _NOISE_HEADING_PREFIX_RE.match(title):
        return None
    if _is_doc_title_noise(title, title_hint=title_hint):
        return None
    if _looks_like_sentence_heading_noise(title):
        return None
    if _PAGE_NUM_RE.fullmatch(title):
        return None

    outline_entry = _resolve_outline_entry(
        raw_title,
        current_page=current_page,
        outline_lookup=outline_lookup,
    ) or _resolve_outline_entry(
        title,
        current_page=current_page,
        outline_lookup=outline_lookup,
    )
    if outline_entry is not None:
        title = clean_heading_title(outline_entry.title)
        level = max(2, min(outline_entry.level + 1, 6))
    else:
        level = min(level, _heading_level_from_plain_text(raw_title), _heading_level_from_plain_text(title))
    return level, title


def build_document_model(
    markdown_text: str,
    *,
    title_hint: str = "",
    outline_entries: Optional[List[DocumentOutlineEntry]] = None,
) -> DocumentModel:
    model = DocumentModel(title=title_hint or None)
    outline_lookup = _build_outline_lookup(outline_entries)
    current_page = 1
    current_section: Optional[DocumentSection] = None
    current_norm = ""
    body_started = False
    algorithm_context_active = False
    source_fence_kind: Optional[str] = None

    def _append_block(block: DocumentBlock) -> None:
        nonlocal current_section
        if current_section is None:
            model.front_matter.append(block)
            return
        current_section.blocks.append(block)
        if block.page_num:
            if current_section.page_start <= 0:
                current_section.page_start = block.page_num
            current_section.page_end = max(current_section.page_end, block.page_num)

    for raw_line in str(markdown_text or "").splitlines():
        stripped = raw_line.rstrip()
        fence_token = stripped.strip()
        if fence_token == "$$":
            source_fence_kind = None if source_fence_kind == "math" else "math"
            continue
        if fence_token.startswith("```"):
            source_fence_kind = None if source_fence_kind == "code" else "code"
            continue
        page_match = _PAGE_MODE_RE.match(stripped.strip()) or _OCR_PAGE_RE.match(stripped.strip())
        if page_match:
            current_page = int(page_match.group("page"))
            _append_block(DocumentBlock(kind="page_marker", text=stripped.strip(), page_num=current_page))
            continue
        if stripped.strip() == "---":
            _append_block(DocumentBlock(kind="separator", text="---", page_num=current_page))
            continue

        inline_heading_info = _extract_inline_heading_and_body(stripped, title_hint=title_hint)
        if inline_heading_info and not body_started:
            level, title, body = inline_heading_info
            current_section = DocumentSection(
                title=title,
                level=level,
                page_start=current_page,
                page_end=current_page,
            )
            if body:
                current_section.blocks.append(DocumentBlock(kind="text", text=body, page_num=current_page))
            model.sections.append(current_section)
            current_norm = normalize_heading_title(title)
            body_started = True
            continue

        heading_info = _extract_heading(
            stripped,
            title_hint=title_hint,
            current_page=current_page,
            current_section_norm=current_norm,
            outline_lookup=outline_lookup,
        )
        if heading_info:
            level, title = heading_info
            normalized = normalize_heading_title(title)
            if not body_started and current_section is None and not _can_start_body_sections(stripped):
                model.front_matter.append(DocumentBlock(kind="text", text=stripped, page_num=current_page))
                continue
            if (
                current_section
                and not current_section.has_meaningful_content()
                and not _can_start_body_sections(stripped)
                and _looks_like_inline_title_fragment(title)
            ):
                current_section.blocks.append(DocumentBlock(kind="text", text=title, page_num=current_page))
                if current_section.page_start <= 0:
                    current_section.page_start = current_page
                current_section.page_end = max(current_section.page_end, current_page)
                continue
            body_started = True
            if current_section and normalized == current_norm and not current_section.has_meaningful_content():
                current_section.title = title
                current_section.level = min(current_section.level, level)
                continue
            current_section = DocumentSection(
                title=title,
                level=level,
                page_start=current_page,
                page_end=current_page,
            )
            model.sections.append(current_section)
            current_norm = normalized
            algorithm_context_active = False
            continue

        if source_fence_kind == "code":
            block_kind = "code"
        elif source_fence_kind == "math":
            block_kind = "code" if algorithm_context_active else "math"
        else:
            block_kind = _classify_body_block_kind(
                stripped,
                current_section_norm=current_norm,
                algorithm_context_active=algorithm_context_active,
            )
        if _ALGORITHM_HEADER_RE.match(stripped):
            algorithm_context_active = True
            block_kind = "code"
        elif algorithm_context_active and block_kind == "text" and stripped.strip():
            algorithm_context_active = False
        _append_block(DocumentBlock(kind=block_kind, text=stripped, page_num=current_page))

    normalized_sections: List[DocumentSection] = []
    previous_norm = ""
    for section in model.sections:
        if _is_doc_title_noise(section.title, title_hint=title_hint):
            model.front_matter.extend(section.blocks)
            continue
        section.blocks = [block for block in section.blocks if block.text.strip() or block.kind in {"page_marker", "separator"}]
        section_norm = normalize_heading_title(section.title)
        if normalized_sections:
            previous = normalized_sections[-1]
            previous_norm = normalize_heading_title(previous.title)
            if previous_norm == "references" and _looks_like_reference_entry_heading(section.title):
                previous.blocks.append(DocumentBlock(kind="text", text=section.title, page_num=section.page_start or previous.page_end))
                previous.blocks.extend(section.blocks)
                previous.page_end = max(previous.page_end, section.page_end)
                continue
            if previous.has_meaningful_content() and _looks_like_inline_title_fragment(section.title):
                previous.blocks.append(DocumentBlock(kind="text", text=section.title, page_num=section.page_start or previous.page_end))
                previous.blocks.extend(section.blocks)
                previous.page_end = max(previous.page_end, section.page_end)
                continue
        if normalized_sections and section_norm and section_norm == previous_norm:
            normalized_sections[-1].blocks.extend(section.blocks)
            normalized_sections[-1].page_end = max(normalized_sections[-1].page_end, section.page_end)
            continue
        normalized_sections.append(section)
        previous_norm = section_norm
    model.sections = normalized_sections
    if outline_lookup:
        model.sections = _split_sections_on_outline_titles(model.sections, outline_lookup=outline_lookup)
    return model


def _split_sections_on_outline_titles(
    sections: List[DocumentSection],
    *,
    outline_lookup: Dict[str, List[DocumentOutlineEntry]],
) -> List[DocumentSection]:
    split_sections: List[DocumentSection] = []
    for section in sections:
        active_section = DocumentSection(
            title=section.title,
            level=section.level,
            page_start=section.page_start,
            page_end=section.page_end,
            blocks=[],
        )
        active_norm = normalize_heading_title(section.title)

        for block in section.blocks:
            stripped = " ".join(str(block.text or "").split()).strip()
            outline_entry = None
            if block.kind == "text" and _looks_like_outline_title_block(stripped):
                outline_entry = _resolve_outline_entry(
                    stripped,
                    current_page=block.page_num or active_section.page_end or active_section.page_start or 1,
                    outline_lookup=outline_lookup,
                )

            if outline_entry is not None:
                outline_norm = normalize_heading_title(outline_entry.title)
                outline_level = max(2, min(outline_entry.level + 1, 6))
                if outline_norm and outline_norm != active_norm:
                    split_sections.append(active_section)
                    active_section = DocumentSection(
                        title=clean_heading_title(outline_entry.title),
                        level=outline_level,
                        page_start=block.page_num or section.page_start,
                        page_end=block.page_num or section.page_start,
                        blocks=[],
                    )
                    active_norm = outline_norm
                    continue

            active_section.blocks.append(block)
            if block.page_num:
                if active_section.page_start <= 0:
                    active_section.page_start = block.page_num
                active_section.page_end = max(active_section.page_end, block.page_num)

        split_sections.append(active_section)

    compact_sections: List[DocumentSection] = []
    for section in split_sections:
        section_norm = normalize_heading_title(section.title)
        if compact_sections and section_norm and section_norm == normalize_heading_title(compact_sections[-1].title):
            compact_sections[-1].blocks.extend(section.blocks)
            compact_sections[-1].page_end = max(compact_sections[-1].page_end, section.page_end)
            continue
        compact_sections.append(section)
    return compact_sections


def _should_keep_empty_heading(title: str) -> bool:
    stripped = " ".join(str(title or "").split()).strip()
    if not stripped:
        return False
    if _COMMON_TITLE_RE.match(stripped):
        return True
    normalized = normalize_heading_title(stripped)
    return normalized in {
        "abstract",
        "references",
        "introduction",
        "preliminaries",
        "methodology",
        "results",
        "conclusion",
        "appendix",
    }


def _build_conservative_document_model(model: DocumentModel, audit: MarkdownQualityAudit) -> DocumentModel:
    conservative = DocumentModel(
        title=model.title,
        front_matter=list(model.front_matter),
        sections=[],
    )
    duplicate_norms = {
        normalize_heading_title(title)
        for title in audit.duplicate_headings
        if normalize_heading_title(title)
    }

    for section in model.sections:
        section_norm = normalize_heading_title(section.title)
        drop_heading = False
        if section.title in audit.suspicious_headings:
            drop_heading = True
        elif not section.has_renderable_content() and not _should_keep_empty_heading(section.title):
            drop_heading = True
        elif section_norm in duplicate_norms and conservative.sections and section_norm == normalize_heading_title(conservative.sections[-1].title):
            drop_heading = True

        if drop_heading:
            if conservative.sections:
                conservative.sections[-1].blocks.extend(section.blocks)
                conservative.sections[-1].page_end = max(
                    conservative.sections[-1].page_end,
                    section.page_end,
                )
            else:
                conservative.front_matter.extend(section.blocks)
            continue

        conservative.sections.append(
            DocumentSection(
                title=section.title,
                level=section.level,
                page_start=section.page_start,
                page_end=section.page_end,
                blocks=list(section.blocks),
            )
        )

    return conservative


def render_document_model(model: DocumentModel) -> str:
    lines: List[str] = []
    title_norm = normalize_heading_title(model.title or "")

    def _flush_grouped_blocks(group_kind: Optional[str], group_texts: List[str]) -> None:
        if not group_kind or not group_texts:
            return
        if group_kind == "math":
            lines.append("$$")
            lines.extend(text.rstrip() for text in group_texts if text.strip())
            lines.append("$$")
            return
        if group_kind == "code":
            lines.append("```text")
            lines.extend(text.rstrip() for text in group_texts if text.strip())
            lines.append("```")
            return

    for block in model.front_matter:
        if not block.text.strip():
            continue
        text = block.text.rstrip()
        if block.kind == "text":
            heading_match = _HEADING_RE.match(text.strip())
            if heading_match:
                text = heading_match.group(2).strip()
            if title_norm and normalize_heading_title(text) == title_norm:
                continue
        lines.append(text)

    for section in model.sections:
        lines.append("")
        lines.append(f"{'#' * max(2, min(section.level, 6))} {section.title}".rstrip())
        grouped_kind: Optional[str] = None
        grouped_texts: List[str] = []
        for block in section.blocks:
            if not block.text.strip():
                continue
            text = block.text.rstrip()
            if block.kind in {"math", "code"}:
                if grouped_kind and grouped_kind != block.kind:
                    _flush_grouped_blocks(grouped_kind, grouped_texts)
                    grouped_kind = None
                    grouped_texts = []
                grouped_kind = block.kind
                grouped_texts.append(text)
                continue
            if grouped_kind:
                _flush_grouped_blocks(grouped_kind, grouped_texts)
                grouped_kind = None
                grouped_texts = []
            if block.kind == "text":
                heading_match = _HEADING_RE.match(text.strip())
                if heading_match:
                    text = heading_match.group(2).strip()
            lines.append(text)
        if grouped_kind:
            _flush_grouped_blocks(grouped_kind, grouped_texts)

    markdown = "\n".join(lines)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"


def normalize_markdown(
    markdown_text: str,
    *,
    title_hint: str = "",
    outline_entries: Optional[List[DocumentOutlineEntry]] = None,
) -> str:
    model = build_document_model(
        markdown_text,
        title_hint=title_hint,
        outline_entries=outline_entries,
    )
    audit = audit_document_model(model)
    if audit.needs_conservative_fallback:
        model = _build_conservative_document_model(model, audit)
    return render_document_model(model)
