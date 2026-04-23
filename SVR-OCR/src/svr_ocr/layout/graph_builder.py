from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..contracts import BlockNode, BlockType, BoundingBox, LayoutGraph, PageImageBundle


class LayoutGraphBuilder(ABC):
    @abstractmethod
    def build(self, page: PageImageBundle) -> LayoutGraph:
        raise NotImplementedError


class HeuristicLayoutGraphBuilder(LayoutGraphBuilder):
    """Interface-first graph builder that can consume existing block metadata.

    This builder is intentionally simple. If upstream code provides layout blocks,
    it converts them into the shared contract. Otherwise it creates a single-page
    fallback block so the rest of the pipeline can still execute.
    """

    def build(self, page: PageImageBundle) -> LayoutGraph:
        raw_blocks = page.metadata.get("blocks", [])
        blocks = [self._coerce_block(raw, idx, page) for idx, raw in enumerate(raw_blocks)]
        if not blocks:
            blocks = [self._fallback_block(page)]
        edges = self._coerce_edges(page.metadata.get("reading_order_edges"), blocks)
        return LayoutGraph(
            page_id=page.page_id,
            page_size=(page.width, page.height),
            blocks=blocks,
            reading_order_edges=edges,
        )

    def _coerce_block(self, raw: dict[str, Any], idx: int, page: PageImageBundle) -> BlockNode:
        bbox_raw = raw.get("bbox") or (0.0, 0.0, float(page.width), float(page.height))
        bbox = BoundingBox(*[float(value) for value in bbox_raw])
        block_type = self._coerce_block_type(raw.get("block_type") or raw.get("type"))
        metadata = dict(raw.get("metadata", {}))
        signals = raw.get("signals") or {}
        for passthrough in (
            "reading_order",
            "font_scale_estimate",
            "ambiguous_order",
            "section_path",
            "source_engine",
        ):
            if passthrough in raw and passthrough not in metadata:
                metadata[passthrough] = raw[passthrough]
        if "order_index" in raw and "reading_order" not in metadata:
            metadata["reading_order"] = raw["order_index"]
        return BlockNode(
            block_id=str(raw.get("block_id") or f"b{idx:04d}"),
            bbox=bbox,
            block_type=block_type,
            confidence=float(raw.get("confidence", raw.get("layout_confidence", 0.0))),
            difficulty=float(raw.get("difficulty", signals.get("difficulty", 0.0))),
            text_density=float(raw.get("text_density", signals.get("text_density", 0.0))),
            source_text=raw.get("text") or raw.get("source_text"),
            column_id=raw.get("column_id"),
            neighbors=[str(value) for value in raw.get("neighbors", [])],
            metadata=metadata,
        )

    def _fallback_block(self, page: PageImageBundle) -> BlockNode:
        return BlockNode(
            block_id="b0000",
            bbox=BoundingBox(0.0, 0.0, float(page.width), float(page.height)),
            block_type=BlockType.PARAGRAPH,
            confidence=0.0,
            difficulty=0.0,
            text_density=0.0,
            source_text=page.metadata.get("seed_text"),
            metadata={"reading_order": 0, "fallback": True},
        )

    def _coerce_edges(
        self,
        raw_edges: Any,
        blocks: list[BlockNode],
    ) -> list[tuple[str, str]]:
        if isinstance(raw_edges, list):
            edges: list[tuple[str, str]] = []
            for item in raw_edges:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    edges.append((str(item[0]), str(item[1])))
            if edges:
                return edges
        ordered = sorted(blocks, key=lambda block: (block.bbox.y0, block.bbox.x0))
        return [
            (ordered[idx].block_id, ordered[idx + 1].block_id)
            for idx in range(max(0, len(ordered) - 1))
        ]

    def _coerce_block_type(self, raw_type: Any) -> BlockType:
        if not raw_type:
            return BlockType.UNKNOWN
        normalized = str(raw_type).strip().lower().replace("-", "_").replace(" ", "_")
        for member in BlockType:
            if member.value == normalized:
                return member
        aliases = {
            "text": BlockType.PARAGRAPH,
            "body": BlockType.PARAGRAPH,
            "dense_paragraph": BlockType.PARAGRAPH,
            "dense_text": BlockType.PARAGRAPH,
            "formula": BlockType.EQUATION,
            "math": BlockType.EQUATION,
            "header": BlockType.HEADER_FOOTER,
            "footer": BlockType.HEADER_FOOTER,
            "bibliography": BlockType.REFERENCE,
        }
        return aliases.get(normalized, BlockType.UNKNOWN)
