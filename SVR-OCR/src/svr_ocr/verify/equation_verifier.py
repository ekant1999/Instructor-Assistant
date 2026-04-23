from __future__ import annotations

from ..contracts import BlockCandidate, BlockNode, LayoutGraph, VerificationBreakdown, VerifiedBlockCandidate
from .base import BlockVerifier


class EquationBlockVerifier(BlockVerifier):
    def verify(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        graph: LayoutGraph,
    ) -> VerifiedBlockCandidate:
        content = candidate.content.strip()
        latex_tokens = ("\\", "$", "\\[", "\\(", "^", "_", "\\begin{", "\\frac")
        has_latex_signal = any(token in content for token in latex_tokens)
        braces_balanced = self._balanced_pairs(content, "{", "}")
        renderable = bool(content) and has_latex_signal and braces_balanced
        failure_reasons: list[str] = []
        if not content:
            failure_reasons.append("empty_equation_candidate")
        if content and not has_latex_signal:
            failure_reasons.append("missing_latex_signal")
        if content and not braces_balanced:
            failure_reasons.append("unbalanced_braces")
        breakdown = VerificationBreakdown(
            renderable=renderable,
            render_score=0.85 if renderable else 0.0,
            structure_score=0.9 if braces_balanced and content else 0.3 if content else 0.0,
            type_consistency_score=1.0 if has_latex_signal else 0.0,
            syntax_validity_score=1.0 if candidate.syntax_valid else 0.0,
            neighbor_consistency_score=0.7 if renderable else 0.0,
            failure_reasons=failure_reasons,
        )
        breakdown = self.score_fusion.finalize(block.block_type, breakdown)
        return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)
