from __future__ import annotations

from ..contracts import BlockType, VerificationBreakdown


class ScoreFusion:
    def finalize(self, block_type: BlockType, breakdown: VerificationBreakdown) -> VerificationBreakdown:
        weights = self._weights_for(block_type)
        breakdown.final_score = (
            weights[0] * (1.0 if breakdown.renderable else 0.0)
            + weights[1] * breakdown.render_score
            + weights[2] * breakdown.structure_score
            + weights[3] * breakdown.syntax_validity_score
            + weights[4] * breakdown.neighbor_consistency_score
        )
        return breakdown

    def _weights_for(self, block_type: BlockType) -> tuple[float, float, float, float, float]:
        if block_type == BlockType.TABLE:
            return (0.15, 0.20, 0.35, 0.20, 0.10)
        if block_type == BlockType.EQUATION:
            return (0.25, 0.30, 0.20, 0.20, 0.05)
        if block_type == BlockType.HEADING:
            return (0.10, 0.20, 0.20, 0.20, 0.30)
        return (0.10, 0.30, 0.20, 0.20, 0.20)
