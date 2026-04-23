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
        normalized_content = {
            block.block_id: self._normalize_block_content(
                block.block_type.value,
                selected_blocks[block.block_id].candidate.content,
            )
            for block in graph.ordered_blocks()
            if block.block_id in selected_blocks
        }
        body_contents = [
            content
            for block in graph.ordered_blocks()
            for content in [normalized_content.get(block.block_id, "")]
            if content and block.metadata.get("position_band") == "body"
        ]
        markdown_parts: list[str] = []
        ordered_ids: list[str] = []
        provenance: dict[str, dict[str, object]] = {}
        for block in graph.ordered_blocks():
            selected = selected_blocks.get(block.block_id)
            if selected is None:
                continue
            content = normalized_content.get(block.block_id, "")
            should_emit = selected.verification.emit
            drop_reason = selected.verification.drop_reason
            if (
                should_emit
                and block.block_type.value == "header_footer"
                and self._duplicated_by_body_prefix(content, body_contents)
            ):
                should_emit = False
                drop_reason = "duplicate_body_prefix"
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
                "drop_reason": drop_reason,
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
        stripped = self._strip_outer_code_fence(content.strip())
        if not stripped:
            return ""
        if stripped == "<<SVR_DROP_HEADER_FOOTER>>":
            return ""
        if block_type == "heading" and not stripped.startswith("#"):
            return f"## {stripped}"
        return stripped

    def _strip_outer_code_fence(self, content: str) -> str:
        if not content.startswith("```"):
            return content
        lines = content.splitlines()
        if not lines:
            return content
        opener = lines[0].strip().lower()
        if opener not in {"```", "```markdown", "```md"}:
            return content
        if len(lines) < 2:
            return ""
        if lines[-1].strip() != "```":
            return "\n".join(lines[1:]).strip()
        return "\n".join(lines[1:-1]).strip()

    def _duplicated_by_body_prefix(self, content: str, body_contents: list[str]) -> bool:
        normalized = self._normalize_for_duplicate_check(content)
        if not normalized:
            return False
        return any(
            self._normalize_for_duplicate_check(body_content).startswith(normalized)
            for body_content in body_contents
        )

    def _normalize_for_duplicate_check(self, content: str) -> str:
        return " ".join(content.lower().replace("#", " ").split())
