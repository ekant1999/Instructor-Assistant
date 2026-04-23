from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts import LayoutGraph, PageImageBundle, PageMarkdownWithProvenance, SelectedBlock


class PageAssembler(ABC):
    @abstractmethod
    def assemble(
        self,
        page: PageImageBundle,
        graph: LayoutGraph,
        selected_blocks: dict[str, SelectedBlock],
    ) -> PageMarkdownWithProvenance:
        raise NotImplementedError


class MarkdownPageAssembler(PageAssembler):
    def assemble(
        self,
        page: PageImageBundle,
        graph: LayoutGraph,
        selected_blocks: dict[str, SelectedBlock],
    ) -> PageMarkdownWithProvenance:
        markdown_parts: list[str] = []
        ordered_ids: list[str] = []
        provenance: dict[str, dict[str, object]] = {}
        for block in graph.ordered_blocks():
            selected = selected_blocks.get(block.block_id)
            if selected is None:
                continue
            content = self._normalize_block_content(block.block_type.value, selected.candidate.content)
            should_emit = selected.verification.emit
            emitted = bool(should_emit and content)
            if emitted:
                markdown_parts.append(content)
                ordered_ids.append(block.block_id)
            provenance[block.block_id] = {
                "block_type": block.block_type.value,
                "prompt_type": selected.candidate.prompt_type.value,
                "verification_score": selected.verification.final_score,
                "repair_count": selected.repair_count,
                "degraded": selected.degraded,
                "emitted": emitted,
                "drop_reason": selected.verification.drop_reason,
                "position_band": block.metadata.get("position_band"),
                "content_preview": content[:200],
                "source_text": block.source_text,
            }
        markdown = "\n\n".join(part for part in markdown_parts if part.strip())
        return PageMarkdownWithProvenance(
            page_id=page.page_id,
            markdown=markdown,
            ordered_blocks=ordered_ids,
            provenance=provenance,
        )

    def _normalize_block_content(self, block_type: str, content: str) -> str:
        stripped = content.strip()
        if not stripped:
            return ""
        if stripped == "<<SVR_DROP_HEADER_FOOTER>>":
            return ""
        if block_type == "heading" and not stripped.startswith("#"):
            return f"## {stripped}"
        return stripped
