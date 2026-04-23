from __future__ import annotations

from ..contracts import BlockCandidate, BlockNode, LayoutGraph, VerificationBreakdown, VerifiedBlockCandidate
from .base import BlockVerifier


class TableBlockVerifier(BlockVerifier):
    def verify(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        graph: LayoutGraph,
    ) -> VerifiedBlockCandidate:
        content = candidate.content.strip().lower()
        renderable = "<table" in content and "</table>" in content
        row_markers = content.count("<tr")
        cell_markers = content.count("<td") + content.count("<th")
        failure_reasons: list[str] = []
        if not renderable:
            failure_reasons.append("missing_table_wrapper")
        if row_markers == 0:
            failure_reasons.append("missing_table_rows")
        if cell_markers == 0:
            failure_reasons.append("missing_table_cells")
        breakdown = VerificationBreakdown(
            renderable=renderable,
            render_score=0.85 if renderable else 0.0,
            structure_score=min(1.0, 0.25 + 0.15 * row_markers + 0.05 * cell_markers),
            type_consistency_score=1.0 if renderable else 0.0,
            syntax_validity_score=1.0 if candidate.syntax_valid else 0.0,
            neighbor_consistency_score=0.8 if renderable else 0.0,
            failure_reasons=failure_reasons,
        )
        breakdown = self.score_fusion.finalize(block.block_type, breakdown)
        return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)
