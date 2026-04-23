from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import SVROCRConfig
from ..contracts import BlockNode, BlockType, LayoutGraph, PageImageBundle, PromptType, RefinementDecision, RefinementPlan


class RefinementPlanner(ABC):
    @abstractmethod
    def plan(self, page: PageImageBundle, graph: LayoutGraph) -> RefinementPlan:
        raise NotImplementedError


class TypedRefinementPlanner(RefinementPlanner):
    def __init__(self, config: SVROCRConfig):
        self.config = config

    def plan(self, page: PageImageBundle, graph: LayoutGraph) -> RefinementPlan:
        decisions: list[RefinementDecision] = []
        for block in graph.blocks:
            decision = self._plan_block(block)
            if decision is not None:
                decisions.append(decision)
        return RefinementPlan(page_id=page.page_id, decisions=decisions)

    def _plan_block(self, block: BlockNode) -> RefinementDecision | None:
        reasons: list[str] = []
        prompt_type = self._prompt_type_for_block(block)
        crop_scale = 1.0
        num_candidates = self.config.candidate_policy.default_candidates
        repair_budget = self.config.repair_policy.default_repairs

        if block.block_type == BlockType.HEADER_FOOTER:
            if not self.config.header_footer.enabled:
                return None
            position_band = str(block.metadata.get("position_band", "unknown"))
            return RefinementDecision(
                block_id=block.block_id,
                prompt_type=PromptType.HEADER_FOOTER,
                crop_scale=self.config.header_footer.crop_scale,
                num_candidates=self.config.header_footer.num_candidates,
                repair_budget=self.config.header_footer.repair_budget,
                reasons=["header_footer_candidate", f"position_{position_band}"],
            )

        if block.block_type == BlockType.TABLE:
            reasons.append("table_block")
            crop_scale = self.config.candidate_policy.very_hard_block_crop_scale
            num_candidates = self.config.candidate_policy.hard_block_candidates
            repair_budget = self.config.repair_policy.very_hard_block_repairs
        elif block.block_type == BlockType.EQUATION:
            reasons.append("equation_block")
            crop_scale = self.config.candidate_policy.hard_block_crop_scale
            num_candidates = self.config.candidate_policy.hard_block_candidates
            repair_budget = self.config.repair_policy.very_hard_block_repairs

        if block.confidence < self.config.thresholds.low_confidence:
            reasons.append("low_confidence")
            crop_scale = max(crop_scale, self.config.candidate_policy.hard_block_crop_scale)
            num_candidates = max(num_candidates, self.config.candidate_policy.hard_block_candidates)
            repair_budget = max(repair_budget, self.config.repair_policy.hard_block_repairs)

        if block.text_density > self.config.thresholds.high_text_density:
            reasons.append("high_text_density")
            prompt_type = PromptType.DENSE_PARAGRAPH
            crop_scale = max(crop_scale, self.config.candidate_policy.very_hard_block_crop_scale)
            num_candidates = max(num_candidates, self.config.candidate_policy.hard_block_candidates)
            repair_budget = max(repair_budget, self.config.repair_policy.hard_block_repairs)

        if block.difficulty > self.config.thresholds.high_difficulty:
            reasons.append("high_difficulty")
            crop_scale = max(crop_scale, self.config.candidate_policy.very_hard_block_crop_scale)
            num_candidates = max(num_candidates, self.config.candidate_policy.very_hard_block_candidates)
            repair_budget = max(repair_budget, self.config.repair_policy.very_hard_block_repairs)

        if bool(block.metadata.get("ambiguous_order")):
            reasons.append("ambiguous_column_order")
            crop_scale = max(crop_scale, self.config.candidate_policy.hard_block_crop_scale)
            num_candidates = max(num_candidates, self.config.candidate_policy.hard_block_candidates)

        if not reasons:
            return None
        return RefinementDecision(
            block_id=block.block_id,
            prompt_type=prompt_type,
            crop_scale=crop_scale,
            num_candidates=num_candidates,
            repair_budget=repair_budget,
            reasons=reasons,
        )

    def _prompt_type_for_block(self, block: BlockNode) -> PromptType:
        if block.block_type == BlockType.HEADING:
            return PromptType.HEADING
        if block.block_type == BlockType.TABLE:
            return PromptType.TABLE
        if block.block_type == BlockType.EQUATION:
            return PromptType.EQUATION
        if block.block_type == BlockType.CAPTION:
            return PromptType.CAPTION
        if block.block_type == BlockType.FOOTNOTE:
            return PromptType.FOOTNOTE
        if block.block_type == BlockType.REFERENCE:
            return PromptType.REFERENCE
        if block.block_type == BlockType.HEADER_FOOTER:
            return PromptType.HEADER_FOOTER
        return PromptType.PARAGRAPH
