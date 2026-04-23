from __future__ import annotations

from ..contracts import BlockCandidate, BlockNode, LayoutGraph, VerificationBreakdown, VerifiedBlockCandidate
from .base import BlockVerifier


class TextBlockVerifier(BlockVerifier):
    def verify(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        graph: LayoutGraph,
    ) -> VerifiedBlockCandidate:
        content = candidate.content.strip()
        renderable = bool(content)
        failure_reasons: list[str] = []
        if not renderable:
            failure_reasons.append("empty_text_candidate")

        if block.source_text:
            source_len = max(1, len(block.source_text.strip()))
            cand_len = len(content)
            ratio = min(source_len, cand_len) / max(source_len, cand_len or 1)
            render_score = ratio
        else:
            render_score = 0.75 if renderable else 0.0

        structure_score = 0.8 if renderable else 0.0
        if block.block_type.value == "heading" and content and not content.lstrip().startswith("#"):
            structure_score -= 0.2
            failure_reasons.append("heading_without_markdown_marker")

        syntax_score = 1.0 if candidate.syntax_valid else 0.0
        neighbor_score = 0.9 if renderable else 0.0
        type_score = 0.9 if renderable else 0.0
        breakdown = VerificationBreakdown(
            renderable=renderable,
            render_score=max(0.0, min(1.0, render_score)),
            structure_score=max(0.0, min(1.0, structure_score)),
            type_consistency_score=type_score,
            syntax_validity_score=syntax_score,
            neighbor_consistency_score=neighbor_score,
            failure_reasons=failure_reasons,
        )
        breakdown = self.score_fusion.finalize(block.block_type, breakdown)
        return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)
