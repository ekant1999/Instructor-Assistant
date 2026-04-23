from __future__ import annotations

import re

from ..contracts import BlockCandidate, BlockNode, LayoutGraph, VerificationBreakdown, VerifiedBlockCandidate
from .base import BlockVerifier


class HeaderFooterBlockVerifier(BlockVerifier):
    """Verifier for margin boilerplate where successful omission is valid output."""

    def __init__(
        self,
        *,
        drop_marker: str = "<<SVR_DROP_HEADER_FOOTER>>",
    ):
        super().__init__()
        self.drop_marker = drop_marker
        self._boilerplate_patterns = [
            re.compile(r"^\d+$", re.IGNORECASE),
            re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
            re.compile(r"\bdoi\s*:", re.IGNORECASE),
            re.compile(r"\barxiv\s*:", re.IGNORECASE),
            re.compile(r"https?://", re.IGNORECASE),
            re.compile(r"\bwww\.", re.IGNORECASE),
            re.compile(r"\bcopyright\b", re.IGNORECASE),
            re.compile(r"\bproceedings\b", re.IGNORECASE),
            re.compile(r"\bconference\b", re.IGNORECASE),
            re.compile(r"\bjournal\b", re.IGNORECASE),
            re.compile(r"\bpreprint\b", re.IGNORECASE),
            re.compile(r"\bsubmitted\s+to\b", re.IGNORECASE),
            re.compile(r"\bvol\.\s*\d+", re.IGNORECASE),
            re.compile(r"\bno\.\s*\d+", re.IGNORECASE),
            re.compile(r"\bpp\.\s*\d+", re.IGNORECASE),
        ]

    def verify(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        graph: LayoutGraph,
    ) -> VerifiedBlockCandidate:
        content = self._strip_code_fences(candidate.content).strip()
        at_page_edge = self._at_page_edge(block, graph)
        failure_reasons: list[str] = []

        if self._is_drop_marker(content):
            breakdown = self._drop_breakdown(
                reason="model_drop_marker",
                score=0.95,
                failure_reasons=[],
            )
            return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)

        if not content:
            breakdown = self._drop_breakdown(
                reason="empty_margin_candidate",
                score=0.80 if at_page_edge else 0.55,
                failure_reasons=[] if at_page_edge else ["empty_non_margin_candidate"],
            )
            return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)

        if self._looks_like_boilerplate(content):
            breakdown = self._drop_breakdown(
                reason="boilerplate_pattern",
                score=0.93,
                failure_reasons=[],
            )
            return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)

        if not at_page_edge:
            failure_reasons.append("header_footer_block_not_at_page_edge")

        syntax_score = 1.0 if candidate.syntax_valid else 0.0
        edge_score = 0.85 if at_page_edge else 0.45
        length_score = self._content_length_score(content)
        final_score = max(0.0, min(1.0, 0.35 * edge_score + 0.35 * length_score + 0.30 * syntax_score))
        breakdown = VerificationBreakdown(
            renderable=True,
            render_score=0.85,
            structure_score=length_score,
            type_consistency_score=edge_score,
            syntax_validity_score=syntax_score,
            neighbor_consistency_score=0.75 if at_page_edge else 0.35,
            final_score=final_score,
            emit=True,
            drop_reason=None,
            failure_reasons=failure_reasons,
        )
        return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)

    def _drop_breakdown(
        self,
        *,
        reason: str,
        score: float,
        failure_reasons: list[str],
    ) -> VerificationBreakdown:
        return VerificationBreakdown(
            renderable=True,
            render_score=1.0,
            structure_score=1.0,
            type_consistency_score=1.0,
            syntax_validity_score=1.0,
            neighbor_consistency_score=1.0,
            final_score=score,
            emit=False,
            drop_reason=reason,
            failure_reasons=failure_reasons,
        )

    def _strip_code_fences(self, content: str) -> str:
        stripped = content.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return stripped.strip("`").strip()

    def _is_drop_marker(self, content: str) -> bool:
        stripped = content.strip()
        if stripped == self.drop_marker:
            return True
        return self.drop_marker in stripped and len(stripped) <= len(self.drop_marker) + 20

    def _looks_like_boilerplate(self, content: str) -> bool:
        compact = " ".join(line.strip() for line in content.splitlines() if line.strip())
        if not compact:
            return True
        if all(not char.isalnum() for char in compact):
            return True
        if self._looks_like_roman_page_number(compact):
            return True
        for pattern in self._boilerplate_patterns:
            if pattern.search(compact):
                return True
        return False

    def _looks_like_roman_page_number(self, content: str) -> bool:
        roman = r"M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
        if re.fullmatch(roman, content) and content:
            return True
        return bool(len(content) <= 4 and re.fullmatch(roman.lower(), content) and content)

    def _at_page_edge(self, block: BlockNode, graph: LayoutGraph) -> bool:
        position_band = str(block.metadata.get("position_band", "")).lower()
        if position_band in {"top", "bottom"}:
            return True
        _, page_height = graph.page_size
        if page_height <= 0:
            return False
        return block.bbox.y0 <= page_height * 0.15 or block.bbox.y1 >= page_height * 0.85

    def _content_length_score(self, content: str) -> float:
        words = re.findall(r"\w+", content)
        if len(words) <= 20:
            return 0.85
        if len(words) <= 60:
            return 0.95
        return 0.75
