from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4

from ..contracts import (
    BlockCandidate,
    BlockNode,
    CropRequest,
    GenerationMetadata,
    PageImageBundle,
    PromptType,
)


@dataclass
class TranscriptionRequest:
    page: PageImageBundle
    block: BlockNode
    crop: CropRequest | None
    prompt_type: PromptType
    prompt_text: str
    num_candidates: int = 1
    repair_context: dict[str, str] = field(default_factory=dict)


class BlockTranscriber(ABC):
    @abstractmethod
    def generate_candidates(self, request: TranscriptionRequest) -> list[BlockCandidate]:
        raise NotImplementedError


class PassthroughBlockTranscriber(BlockTranscriber):
    """Scaffold transcriber used until real model integration is wired in."""

    def __init__(self, model_name: str = "svr-ocr-scaffold"):
        self.model_name = model_name

    def generate_candidates(self, request: TranscriptionRequest) -> list[BlockCandidate]:
        base_text = (request.block.source_text or "").strip()
        if not base_text:
            base_text = self._default_content_for_prompt(request.prompt_type)
        candidates: list[BlockCandidate] = []
        for idx in range(request.num_candidates):
            suffix = f"_{idx}" if request.num_candidates > 1 else ""
            content = base_text
            if request.repair_context:
                failure_reasons = request.repair_context.get("failure_reasons", "")
                if failure_reasons:
                    content = content + f"\n<!-- repair-context: {failure_reasons} -->"
            candidate = BlockCandidate(
                page_id=request.page.page_id,
                block_id=request.block.block_id,
                candidate_id=f"{request.block.block_id}_{uuid4().hex[:8]}{suffix}",
                block_type=request.block.block_type,
                prompt_type=request.prompt_type,
                content=content,
                raw_model_output=content,
                syntax_valid=True,
                generation_metadata=GenerationMetadata(
                    model=self.model_name,
                    prompt_type=request.prompt_type,
                    temperature=0.0,
                    max_tokens=None,
                    extra={"scaffold": True},
                ),
                is_repair=bool(request.repair_context),
            )
            candidates.append(candidate)
        return candidates

    def _default_content_for_prompt(self, prompt_type: PromptType) -> str:
        defaults = {
            PromptType.TABLE: "<table><tr><td></td></tr></table>",
            PromptType.REPAIR_TABLE: "<table><tr><td></td></tr></table>",
            PromptType.EQUATION: r"\[\]",
            PromptType.REPAIR_EQUATION: r"\[\]",
            PromptType.HEADING: "## Untitled Heading",
            PromptType.HEADER_FOOTER: "<<SVR_DROP_HEADER_FOOTER>>",
            PromptType.REPAIR_HEADER_FOOTER: "<<SVR_DROP_HEADER_FOOTER>>",
        }
        return defaults.get(prompt_type, "")
