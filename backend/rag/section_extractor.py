"""
Section extraction utilities for PDF ingestion.

Fallback chain:
1) arXiv source parsing (if source URL resolves to an arXiv ID)
2) GROBID TEI parsing (if GROBID_URL is configured)
3) Heuristic heading extraction from PDF text blocks

The output is used to annotate each extracted PDF block with section metadata
before chunking and embedding.
"""
from __future__ import annotations

import io
import logging
import os
import re
import tarfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import pymupdf

logger = logging.getLogger(__name__)


SECTION_PATTERNS: List[Tuple[str, List[str]]] = [
    ("abstract", [r"\babstract\b"]),
    ("introduction", [r"\bintroduction\b", r"\boverview\b"]),
    ("notation", [r"\bnotation(s)?\b"]),
    ("related_work", [r"\brelated work\b", r"\bliterature review\b"]),
    ("methodology", [r"\bmethod(s|ology)?\b", r"\bapproach\b", r"\bproblem formulation\b"]),
    ("achievability", [r"\bachievab(?:ility|le)\b"]),
    ("capacity_bound", [r"\bcapacity\b.*\bbound\b", r"\bupper bound\b", r"\blower bound\b"]),
    ("experiments", [r"\bexperiment(s)?\b", r"\bevaluation\b"]),
    ("results", [r"\bresult(s)?\b", r"\bfindings\b", r"\bperformance\b"]),
    ("discussion", [r"\bdiscussion\b", r"\bimplications\b"]),
    ("numerical_applications", [r"\bnumerical application(s)?\b", r"\bnumerical result(s)?\b", r"\bsimulation(s)?\b"]),
    ("conclusion", [r"\bconclusion(s)?\b", r"\bfuture work\b"]),
    ("appendix", [r"\bappendix\b", r"\bsupplementary\b"]),
    ("acknowledgements", [r"\backnowledg(e)?ments?\b"]),
    ("references", [r"\breferences?\b", r"\bbibliography\b"]),
]


_ARXIV_ID_RE = re.compile(
    r"(?:(?:https?://)?arxiv\.org/(?:abs|pdf|e-print)/)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)
_LATEX_SECTION_RE = re.compile(
    r"\\(?P<kind>section|subsection|subsubsection)\*?\{(?P<title>[^{}]{1,220})\}",
    re.IGNORECASE | re.MULTILINE,
)
_LATEX_ABSTRACT_RE = re.compile(
    r"\\begin\{abstract\}(?P<body>.*?)\\end\{abstract\}",
    re.IGNORECASE | re.DOTALL,
)
_HEADING_NUMBER_PREFIX_RE = re.compile(
    r"^\s*(?:[ivxlcdm]+\.?|[a-z]\)|\d+(?:\.\d+){0,3}\.?)\s+",
    re.IGNORECASE,
)
_ROMAN_HEADING_RE = re.compile(r"^\s*(?P<num>[IVXLCDM]+)\.\s+(?P<rest>.+)$")
_NUMERIC_HEADING_RE = re.compile(r"^\s*(?P<num>\d+(?:\.\d+){0,3})\.?\s+(?P<rest>.+)$")
_HEADING_NOISE_RE = re.compile(r"^(table|fig\.?|figure|algorithm|lemma|theorem)\b", re.IGNORECASE)


@dataclass
class HeadingCandidate:
    title: str
    level: int
    source: str
    confidence: float
    block_hint: Optional[int] = None
    page_hint: Optional[int] = None


@dataclass
class SectionSpan:
    index: int
    title: str
    canonical: str
    level: int
    source: str
    confidence: float
    start_idx: int
    end_idx: int
    start_page: int
    end_page: int


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip().lower()
    value = _HEADING_NUMBER_PREFIX_RE.sub("", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _clean_heading_title(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", value)
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = _HEADING_NUMBER_PREFIX_RE.sub("", value)
    return value.strip(" .:-")


def canonicalize_heading(raw_title: str) -> str:
    normalized = _normalize_text(raw_title)
    if not normalized:
        return "other"
    for canonical, patterns in SECTION_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return canonical
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    if not slug:
        return "other"
    return "_".join(slug.split("_")[:10])


def _extract_arxiv_id(source_url: Optional[str]) -> Optional[str]:
    if not source_url:
        return None
    value = source_url.strip()
    if not value:
        return None
    match = _ARXIV_ID_RE.search(value)
    if not match:
        return None
    arxiv_id = match.group("id")
    if arxiv_id.lower().endswith(".pdf"):
        arxiv_id = arxiv_id[:-4]
    return arxiv_id


def _strip_latex_comments(content: str) -> str:
    cleaned_lines: List[str] = []
    for line in content.splitlines():
        # keep escaped percent signs, strip comments
        stripped = re.sub(r"(?<!\\)%.*$", "", line)
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def _pick_main_tex(tex_candidates: List[Tuple[str, str]]) -> Optional[str]:
    best_content: Optional[str] = None
    best_score = -1
    for _, content in tex_candidates:
        score = 0
        if "\\begin{document}" in content:
            score += 10
        score += len(_LATEX_SECTION_RE.findall(content))
        if _LATEX_ABSTRACT_RE.search(content):
            score += 3
        if score > best_score:
            best_score = score
            best_content = content
    return best_content


def _parse_latex_headings(tex_content: str) -> List[HeadingCandidate]:
    cleaned = _strip_latex_comments(tex_content)
    headings: List[HeadingCandidate] = []
    include_subsections = os.getenv("ARXIV_INCLUDE_SUBSECTIONS", "0").strip().lower() in {"1", "true", "yes"}

    abstract_match = _LATEX_ABSTRACT_RE.search(cleaned)
    if abstract_match:
        headings.append(
            HeadingCandidate(
                title="Abstract",
                level=1,
                source="arxiv_source",
                confidence=0.95,
            )
        )

    level_map = {"section": 1, "subsection": 2, "subsubsection": 3}
    for match in _LATEX_SECTION_RE.finditer(cleaned):
        raw_title = _clean_heading_title(match.group("title") or "")
        if not raw_title:
            continue
        kind = (match.group("kind") or "section").lower()
        if kind != "section" and not include_subsections:
            continue
        headings.append(
            HeadingCandidate(
                title=raw_title,
                level=level_map.get(kind, 1),
                source="arxiv_source",
                confidence=0.92 if kind == "section" else 0.85,
            )
        )

    if re.search(r"\\begin\{thebibliography\}|\\bibliography\s*\{", cleaned, re.IGNORECASE):
        headings.append(
            HeadingCandidate(
                title="References",
                level=1,
                source="arxiv_source",
                confidence=0.9,
            )
        )

    return _dedupe_headings(headings)


def _extract_headings_from_arxiv_source(source_url: Optional[str]) -> List[HeadingCandidate]:
    arxiv_id = _extract_arxiv_id(source_url)
    if not arxiv_id:
        return []

    source_endpoint = f"https://arxiv.org/e-print/{arxiv_id}"
    timeout = int(os.getenv("ARXIV_SOURCE_TIMEOUT", "20"))
    try:
        response = requests.get(source_endpoint, timeout=timeout)
        if response.status_code != 200 or not response.content:
            return []
    except Exception as exc:
        logger.warning("arXiv source download failed for %s: %s", arxiv_id, exc)
        return []

    tex_candidates: List[Tuple[str, str]] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                if not member.name.lower().endswith(".tex"):
                    continue
                file_obj = archive.extractfile(member)
                if not file_obj:
                    continue
                try:
                    content = file_obj.read().decode("utf-8", errors="ignore")
                except Exception:
                    continue
                tex_candidates.append((member.name, content))
    except Exception as exc:
        logger.warning("Failed to parse arXiv source tarball for %s: %s", arxiv_id, exc)
        return []

    if not tex_candidates:
        return []
    main_tex = _pick_main_tex(tex_candidates)
    if not main_tex:
        return []
    return _parse_latex_headings(main_tex)


def _extract_headings_from_pdf_toc(pdf_path: Path) -> List[HeadingCandidate]:
    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception as exc:
        logger.warning("Failed to open PDF for TOC extraction %s: %s", pdf_path, exc)
        return []

    try:
        toc = doc.get_toc()
    except Exception as exc:
        logger.warning("Failed to read PDF TOC for %s: %s", pdf_path, exc)
        doc.close()
        return []

    doc.close()

    if not toc:
        return []

    has_level_one = any(int(item[0]) == 1 for item in toc if len(item) >= 3)
    allowed_levels = {1} if has_level_one else {1, 2}
    headings: List[HeadingCandidate] = []
    seen = set()

    for item in toc:
        if len(item) < 3:
            continue
        try:
            level = int(item[0])
            title = _clean_heading_title(str(item[1] or ""))
            page_no = int(item[2])
        except Exception:
            continue

        if level not in allowed_levels:
            continue
        if page_no < 1:
            continue
        if not _is_reasonable_heading_title(title):
            continue

        normalized = _normalize_text(title)
        key = (normalized, page_no)
        if not normalized or key in seen:
            continue
        seen.add(key)

        headings.append(
            HeadingCandidate(
                title=title,
                level=min(max(level, 1), 3),
                source="pdf_toc",
                confidence=0.97 if level == 1 else 0.9,
                page_hint=page_no,
            )
        )

    return _dedupe_headings(headings)


def _xml_text(node: Optional[ET.Element]) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split()).strip()


def _extract_headings_with_grobid(pdf_path: Path) -> List[HeadingCandidate]:
    grobid_url = os.getenv("GROBID_URL", "").strip()
    if not grobid_url:
        return []

    endpoint = grobid_url.rstrip("/") + "/api/processFulltextDocument"
    timeout = int(os.getenv("GROBID_TIMEOUT", "45"))
    try:
        with pdf_path.open("rb") as handle:
            response = requests.post(
                endpoint,
                files={"input": (pdf_path.name, handle, "application/pdf")},
                data={
                    "consolidateHeader": "0",
                    "consolidateCitations": "0",
                    "includeRawCitations": "0",
                },
                timeout=timeout,
            )
        response.raise_for_status()
        xml_text = response.text
        if not xml_text.strip():
            return []
    except Exception as exc:
        logger.warning("GROBID extraction failed for %s: %s", pdf_path, exc)
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("GROBID returned invalid XML for %s: %s", pdf_path, exc)
        return []

    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    headings: List[HeadingCandidate] = []
    include_subsections = os.getenv("GROBID_INCLUDE_SUBSECTIONS", "0").strip().lower() in {"1", "true", "yes"}

    abstract_node = root.find(".//tei:abstract", ns)
    if abstract_node is not None:
        headings.append(
            HeadingCandidate(
                title="Abstract",
                level=1,
                source="grobid",
                confidence=0.88,
            )
        )

    for div in root.findall(".//tei:div", ns):
        head = div.find("./tei:head", ns)
        title = _clean_heading_title(_xml_text(head))
        if not title:
            continue
        n_attr = (head.get("n") if head is not None else None) or ""
        level = 1
        if "." in n_attr:
            level = min(3, n_attr.count(".") + 1)
        if level > 1 and not include_subsections:
            continue
        headings.append(
            HeadingCandidate(
                title=title,
                level=level,
                source="grobid",
                confidence=0.84 if level == 1 else 0.78,
            )
        )

    return _dedupe_headings(headings)


def _is_upper_token(token: str) -> bool:
    cleaned = re.sub(r"[^A-Za-z0-9&()/-]+", "", token)
    if not cleaned:
        return False
    letters = [ch for ch in cleaned if ch.isalpha()]
    if not letters:
        return False
    uppercase = sum(1 for ch in letters if ch.isupper())
    return uppercase / len(letters) >= 0.8


def _extract_roman_heading_title(text: str) -> str:
    match = _ROMAN_HEADING_RE.match(text.strip())
    if not match:
        return ""
    rest = match.group("rest").strip()
    if not rest:
        return ""
    tokens = rest.split()
    title_tokens: List[str] = []
    for token in tokens[:24]:
        if _is_upper_token(token):
            title_tokens.append(token)
            continue
        break
    if not title_tokens:
        return ""
    return _clean_heading_title(" ".join(title_tokens))


def _extract_numeric_heading_title(text: str) -> str:
    match = _NUMERIC_HEADING_RE.match(text.strip())
    if not match:
        return ""
    rest = match.group("rest").strip()
    if not rest:
        return ""
    tokens = rest.split()
    title_tokens: List[str] = []
    for token in tokens[:20]:
        cleaned = re.sub(r"[^A-Za-z0-9&()/-]+", "", token)
        if not cleaned:
            continue
        if cleaned[0].islower() and len(title_tokens) >= 2:
            break
        title_tokens.append(token)
    if not title_tokens:
        return ""
    return _clean_heading_title(" ".join(title_tokens))


def _is_reasonable_heading_title(title: str) -> bool:
    cleaned = _clean_heading_title(title)
    normalized = _normalize_text(cleaned)
    if not normalized:
        return False
    if _HEADING_NOISE_RE.match(normalized):
        return False
    tokens = normalized.split()
    if not tokens:
        return False
    if len(tokens) == 1 and len(tokens[0]) < 4:
        return False
    if sum(len(token) for token in tokens) < 4:
        return False
    short_tokens = sum(1 for token in tokens if len(token) <= 1)
    if len(tokens) > 1 and short_tokens >= len(tokens) // 2:
        return False
    return True


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_heuristic_headings(blocks: List[Dict[str, Any]]) -> List[HeadingCandidate]:
    body_font_candidates: List[float] = []
    for block in blocks:
        metadata = block.get("metadata")
        if not isinstance(metadata, dict):
            continue
        char_count = int(_safe_float(metadata.get("char_count"), 0))
        line_count = int(_safe_float(metadata.get("line_count"), 0))
        avg_font = _safe_float(metadata.get("avg_font_size"), 0.0)
        if char_count >= 80 and line_count >= 2 and avg_font > 0:
            body_font_candidates.append(avg_font)

    body_font = 0.0
    if body_font_candidates:
        sorted_fonts = sorted(body_font_candidates)
        body_font = sorted_fonts[len(sorted_fonts) // 2]

    headings: List[HeadingCandidate] = []
    for idx, block in enumerate(blocks):
        raw_text = str(block.get("text") or "").replace("\x00", "").strip()
        if not raw_text:
            continue
        metadata = block.get("metadata")
        first_line_raw = ""
        if isinstance(metadata, dict):
            first_line_raw = str(metadata.get("first_line") or "")
        if not first_line_raw:
            first_line_raw = raw_text.splitlines()[0]
        line = " ".join(first_line_raw.split())
        if not line:
            continue

        candidate_title = ""
        line_l = line.lower()
        if line_l.startswith("abstract"):
            candidate_title = "Abstract"
        elif line_l.startswith("references"):
            candidate_title = "References"
        else:
            numeric_title = _extract_numeric_heading_title(line)
            if numeric_title:
                candidate_title = numeric_title
            roman_title = _extract_roman_heading_title(line) if not candidate_title else ""
            if roman_title:
                candidate_title = roman_title
            else:
                words = line.split()
                if 1 <= len(words) <= 12 and all(_is_upper_token(token) for token in words):
                    candidate_title = _clean_heading_title(line)

        if not candidate_title and isinstance(metadata, dict):
            max_font = _safe_float(metadata.get("max_font_size"), 0.0)
            bold_ratio = _safe_float(metadata.get("bold_ratio"), 0.0)
            line_count = int(_safe_float(metadata.get("line_count"), 1))
            words = line.split()
            title_case_words = sum(1 for token in words if token[:1].isupper())
            looks_title_case = len(words) <= 12 and title_case_words >= max(2, len(words) - 1)
            font_prominent = body_font > 0 and max_font >= (body_font + 1.0)
            if (
                looks_title_case
                and line_count <= 2
                and len(line) <= 120
                and (font_prominent or bold_ratio >= 0.45)
                and not line_l.startswith(("figure", "table", "arxiv:", "http://", "https://"))
            ):
                candidate_title = _clean_heading_title(line)

        if not candidate_title:
            continue
        if not _is_reasonable_heading_title(candidate_title):
            continue

        headings.append(
            HeadingCandidate(
                title=candidate_title,
                level=1,
                source="heuristic",
                confidence=0.72,
                block_hint=idx,
                page_hint=int(block.get("page_no") or 1),
            )
        )
    return _dedupe_headings(headings)


def _dedupe_headings(headings: Iterable[HeadingCandidate]) -> List[HeadingCandidate]:
    deduped: List[HeadingCandidate] = []
    seen = set()
    for heading in headings:
        normalized = _normalize_text(heading.title)
        key = (normalized, heading.level)
        if not normalized or key in seen:
            continue
        seen.add(key)
        deduped.append(heading)
    return deduped


def _heading_match_score(heading_norm: str, block_norm: str) -> float:
    if not heading_norm or not block_norm:
        return 0.0
    if heading_norm in block_norm:
        return 1.0
    # Compare with the beginning of the block where headings usually appear.
    short_block = " ".join(block_norm.split()[:20])
    score = SequenceMatcher(None, heading_norm, short_block).ratio()
    heading_tokens = heading_norm.split()
    if heading_tokens:
        token_hits = sum(1 for token in heading_tokens if token in short_block)
        score = max(score, token_hits / len(heading_tokens))
    return score


def _align_headings_to_spans(
    headings: List[HeadingCandidate],
    blocks: List[Dict[str, Any]],
) -> List[SectionSpan]:
    if not headings or not blocks:
        return []

    normalized_blocks = [_normalize_text(str(block.get("text") or "")[:260]) for block in blocks]
    page_ranges: Dict[int, Tuple[int, int]] = {}
    for idx, block in enumerate(blocks):
        page_no = int(block.get("page_no") or 1)
        if page_no in page_ranges:
            first_idx, _ = page_ranges[page_no]
            page_ranges[page_no] = (first_idx, idx)
        else:
            page_ranges[page_no] = (idx, idx)

    max_page = max(page_ranges.keys()) if page_ranges else 1

    matched: List[Tuple[HeadingCandidate, int, float]] = []
    search_start = 0

    for heading in headings:
        heading_norm = _normalize_text(heading.title)
        if not heading_norm:
            continue
        best_idx = -1
        best_score = 0.0

        if heading.block_hint is not None and search_start <= heading.block_hint < len(blocks):
            best_idx = heading.block_hint
            best_score = 1.0
        else:
            scan_start = search_start
            scan_end = len(blocks) - 1
            if heading.page_hint is not None and heading.page_hint in page_ranges:
                page_start, _ = page_ranges[heading.page_hint]
                scan_start = max(scan_start, page_start)

                end_page = min(max_page, heading.page_hint + 2)
                end_idx = None
                for page in range(end_page, heading.page_hint - 1, -1):
                    if page in page_ranges:
                        _, end_candidate = page_ranges[page]
                        end_idx = end_candidate
                        break
                if end_idx is not None:
                    scan_end = max(scan_start, end_idx)

            for idx in range(scan_start, scan_end + 1):
                score = _heading_match_score(heading_norm, normalized_blocks[idx])
                if score > best_score:
                    best_score = score
                    best_idx = idx

        min_score = 0.65
        if heading.source == "pdf_toc":
            min_score = 0.38
        elif heading.source == "grobid":
            min_score = 0.58
        elif heading.source == "arxiv_source":
            min_score = 0.55
        elif heading.source == "heuristic":
            min_score = 0.42

        if (
            (best_idx < 0 or best_score < min_score)
            and heading.page_hint is not None
            and heading.page_hint in page_ranges
        ):
            best_idx = max(search_start, page_ranges[heading.page_hint][0])
            if best_idx < len(blocks):
                if heading.source == "pdf_toc":
                    best_score = 0.72
                elif heading.source in {"arxiv_source", "grobid"}:
                    best_score = 0.62

        if best_idx >= 0 and best_score >= min_score:
            matched.append((heading, best_idx, best_score))
            search_start = max(search_start, best_idx + 1)

    if not matched:
        return []

    # Remove duplicates that resolve to the same block index.
    deduped_matches: List[Tuple[HeadingCandidate, int, float]] = []
    for item in matched:
        if deduped_matches and item[1] == deduped_matches[-1][1]:
            if item[2] > deduped_matches[-1][2]:
                deduped_matches[-1] = item
            continue
        deduped_matches.append(item)

    spans: List[SectionSpan] = []
    first_idx = deduped_matches[0][1]
    if first_idx > 0:
        first_block = blocks[0]
        before_block = blocks[first_idx - 1]
        spans.append(
            SectionSpan(
                index=0,
                title="Front Matter",
                canonical="front_matter",
                level=1,
                source="fallback",
                confidence=0.4,
                start_idx=0,
                end_idx=first_idx - 1,
                start_page=int(first_block.get("page_no") or 1),
                end_page=int(before_block.get("page_no") or first_block.get("page_no") or 1),
            )
        )

    for i, (heading, start_idx, score) in enumerate(deduped_matches):
        end_idx = deduped_matches[i + 1][1] - 1 if i + 1 < len(deduped_matches) else len(blocks) - 1
        if end_idx < start_idx:
            continue
        start_block = blocks[start_idx]
        end_block = blocks[end_idx]
        span_confidence = round((heading.confidence * 0.7) + (score * 0.3), 3)
        spans.append(
            SectionSpan(
                index=len(spans),
                title=heading.title,
                canonical=canonicalize_heading(heading.title),
                level=heading.level,
                source=heading.source,
                confidence=span_confidence,
                start_idx=start_idx,
                end_idx=end_idx,
                start_page=int(start_block.get("page_no") or 1),
                end_page=int(end_block.get("page_no") or start_block.get("page_no") or 1),
            )
        )

    return spans


def _apply_spans_to_blocks(blocks: List[Dict[str, Any]], spans: List[SectionSpan]) -> None:
    if not spans:
        fallback_span = SectionSpan(
            index=0,
            title="Document Body",
            canonical="other",
            level=1,
            source="fallback",
            confidence=0.35,
            start_idx=0,
            end_idx=max(0, len(blocks) - 1),
            start_page=int((blocks[0].get("page_no") if blocks else 1) or 1),
            end_page=int((blocks[-1].get("page_no") if blocks else 1) or 1),
        )
        spans = [fallback_span]

    for span in spans:
        for idx in range(span.start_idx, span.end_idx + 1):
            if idx < 0 or idx >= len(blocks):
                continue
            block = blocks[idx]
            metadata = block.setdefault("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
                block["metadata"] = metadata
            metadata["section_title"] = span.title
            metadata["section_canonical"] = span.canonical
            metadata["section_level"] = span.level
            metadata["section_source"] = span.source
            metadata["section_confidence"] = span.confidence
            metadata["section_index"] = span.index


def annotate_blocks_with_sections(
    blocks: List[Dict[str, Any]],
    pdf_path: Path,
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Annotate block metadata with canonical section information.

    Returns a report dictionary for ingestion diagnostics.
    """
    if not blocks:
        return {
            "strategy": "none",
            "candidate_headings": 0,
            "matched_headings": 0,
            "sections": [],
        }

    def _count_non_front(span_items: List[SectionSpan]) -> int:
        return sum(1 for item in span_items if item.canonical != "front_matter")

    def _strategy_score(source_name: str, heading_items: List[HeadingCandidate], span_items: List[SectionSpan]) -> float:
        matched_non_front = _count_non_front(span_items)
        if matched_non_front <= 0:
            return -1.0
        coverage = matched_non_front / max(1, len(heading_items))
        confidences = [item.confidence for item in span_items if item.canonical != "front_matter"]
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        source_bonus = {
            "pdf_toc": 1.25,
            "arxiv_source": 1.1,
            "grobid": 1.0,
            "heuristic": 0.7,
        }.get(source_name, 0.6)
        return source_bonus + (matched_non_front * 0.25) + (coverage * 1.5) + (avg_confidence * 0.5)

    strategy = "heuristic"
    headings: List[HeadingCandidate] = []
    spans: List[SectionSpan] = []

    heuristic_headings = _extract_heuristic_headings(blocks)

    # Prefer local PDF outline if it already gives strong section coverage.
    toc_headings = _extract_headings_from_pdf_toc(pdf_path)
    if toc_headings:
        toc_canonicals = {canonicalize_heading(item.title) for item in toc_headings}
        abstract_heading = next(
            (item for item in heuristic_headings if canonicalize_heading(item.title) == "abstract"),
            None,
        )
        references_heading = next(
            (item for item in heuristic_headings if canonicalize_heading(item.title) == "references"),
            None,
        )
        if abstract_heading and "abstract" not in toc_canonicals:
            toc_headings = [abstract_heading, *toc_headings]
        if references_heading and "references" not in toc_canonicals:
            toc_headings = [*toc_headings, references_heading]
        toc_headings = _dedupe_headings(toc_headings)

    toc_spans = _align_headings_to_spans(toc_headings, blocks) if toc_headings else []
    if toc_headings and _count_non_front(toc_spans) >= 3:
        strategy = "pdf_toc"
        headings = toc_headings
        spans = toc_spans
    else:
        candidates: List[Tuple[str, List[HeadingCandidate], List[SectionSpan], float]] = []
        strategy_inputs = [
            ("pdf_toc", toc_headings),
            ("arxiv_source", _extract_headings_from_arxiv_source(source_url)),
            ("grobid", _extract_headings_with_grobid(pdf_path)),
            ("heuristic", heuristic_headings),
        ]

        for source_name, source_headings in strategy_inputs:
            if not source_headings:
                continue
            source_spans = _align_headings_to_spans(source_headings, blocks)
            score = _strategy_score(source_name, source_headings, source_spans)
            candidates.append((source_name, source_headings, source_spans, score))

        if candidates:
            candidates.sort(key=lambda item: item[3], reverse=True)
            strategy, headings, spans, _ = candidates[0]
        else:
            headings = heuristic_headings
            spans = _align_headings_to_spans(headings, blocks)
            strategy = "heuristic"

    _apply_spans_to_blocks(blocks, spans)

    report_sections = [
        {
            "index": span.index,
            "title": span.title,
            "canonical": span.canonical,
            "level": span.level,
            "source": span.source,
            "confidence": span.confidence,
            "start_page": span.start_page,
            "end_page": span.end_page,
            "start_block_index": span.start_idx,
            "end_block_index": span.end_idx,
        }
        for span in spans
    ]

    return {
        "strategy": strategy,
        "candidate_headings": len(headings),
        "matched_headings": len(spans),
        "sections": report_sections,
    }
