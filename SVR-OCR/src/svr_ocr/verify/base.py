from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts import BlockCandidate, BlockNode, BlockType, LayoutGraph, VerificationBreakdown, VerifiedBlockCandidate
from .score_fusion import ScoreFusion


class BlockVerifier(ABC):
    def __init__(self, score_fusion: ScoreFusion | None = None):
        self.score_fusion = score_fusion or ScoreFusion()

    @abstractmethod
    def verify(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        graph: LayoutGraph,
    ) -> VerifiedBlockCandidate:
        raise NotImplementedError

    def _balanced_pairs(self, content: str, left: str, right: str) -> bool:
        return content.count(left) == content.count(right)


class VerifierRouter:
    def __init__(
        self,
        text_verifier: BlockVerifier,
        table_verifier: BlockVerifier,
        equation_verifier: BlockVerifier,
        header_footer_verifier: BlockVerifier | None = None,
    ):
        self.text_verifier = text_verifier
        self.table_verifier = table_verifier
        self.equation_verifier = equation_verifier
        self.header_footer_verifier = header_footer_verifier

    def verify(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        graph: LayoutGraph,
    ) -> VerifiedBlockCandidate:
        if block.block_type == BlockType.TABLE:
            return self.table_verifier.verify(block, candidate, graph)
        if block.block_type == BlockType.EQUATION:
            return self.equation_verifier.verify(block, candidate, graph)
        if block.block_type == BlockType.HEADER_FOOTER and self.header_footer_verifier is not None:
            return self.header_footer_verifier.verify(block, candidate, graph)
        return self.text_verifier.verify(block, candidate, graph)

    def degraded_result(
        self,
        block: BlockNode,
        candidate: BlockCandidate,
        reason: str,
    ) -> VerifiedBlockCandidate:
        breakdown = VerificationBreakdown(
            renderable=False,
            final_score=0.0,
            failure_reasons=[reason],
        )
        return VerifiedBlockCandidate(candidate=candidate, verification=breakdown)
