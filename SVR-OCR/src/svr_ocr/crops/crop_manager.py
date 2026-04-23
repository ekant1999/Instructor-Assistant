from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts import CropRequest, LayoutGraph, PageImageBundle, RefinementPlan


class CropManager(ABC):
    @abstractmethod
    def build_requests(
        self,
        page: PageImageBundle,
        graph: LayoutGraph,
        plan: RefinementPlan,
    ) -> dict[str, CropRequest]:
        raise NotImplementedError


class SimpleCropManager(CropManager):
    def __init__(self, context_margin: int = 24):
        self.context_margin = context_margin

    def build_requests(
        self,
        page: PageImageBundle,
        graph: LayoutGraph,
        plan: RefinementPlan,
    ) -> dict[str, CropRequest]:
        block_by_id = {block.block_id: block for block in graph.blocks}
        requests: dict[str, CropRequest] = {}
        for decision in plan.decisions:
            block = block_by_id[decision.block_id]
            bbox = block.bbox.expanded(self.context_margin, page.width, page.height)
            requests[decision.block_id] = CropRequest(
                page_id=page.page_id,
                block_id=decision.block_id,
                bbox=bbox,
                scale=decision.crop_scale,
                image_path=page.image_path,
                context_margin=self.context_margin,
                metadata={"block_type": block.block_type.value},
            )
        return requests
