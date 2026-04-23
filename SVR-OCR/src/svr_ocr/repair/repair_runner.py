from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts import BlockNode, CropRequest, PromptType, RefinementDecision, VerifiedBlockCandidate
from ..prompts.library import PromptLibrary
from ..transcribe.block_runner import BlockTranscriber, TranscriptionRequest
from ..transcribe.candidate_store import CandidateStore


class RepairRunner(ABC):
    @abstractmethod
    def attempt_repair(
        self,
        page,
        block: BlockNode,
        crop: CropRequest | None,
        decision: RefinementDecision,
        failed: VerifiedBlockCandidate,
        transcriber: BlockTranscriber,
        prompt_library: PromptLibrary,
        candidate_store: CandidateStore,
    ):
        raise NotImplementedError


class SimpleRepairRunner(RepairRunner):
    def attempt_repair(
        self,
        page,
        block: BlockNode,
        crop: CropRequest | None,
        decision: RefinementDecision,
        failed: VerifiedBlockCandidate,
        transcriber: BlockTranscriber,
        prompt_library: PromptLibrary,
        candidate_store: CandidateStore,
    ):
        repair_prompt_type = self._repair_prompt_type(decision.prompt_type)
        if repair_prompt_type is None:
            return []
        prompt_text = prompt_library.render(
            repair_prompt_type,
            prior_output=failed.candidate.content,
            failure_reasons=", ".join(failed.verification.failure_reasons),
            block_type=block.block_type.value,
            source_text=block.source_text or "",
        )
        request = TranscriptionRequest(
            page=page,
            block=block,
            crop=crop,
            prompt_type=repair_prompt_type,
            prompt_text=prompt_text,
            num_candidates=1,
            repair_context={
                "failure_reasons": ", ".join(failed.verification.failure_reasons),
                "prior_output": failed.candidate.content,
            },
        )
        candidates = transcriber.generate_candidates(request)
        candidate_store.save(block.block_id, candidates)
        return candidates

    def _repair_prompt_type(self, prompt_type: PromptType) -> PromptType | None:
        mapping = {
            PromptType.PARAGRAPH: PromptType.REPAIR_PARAGRAPH,
            PromptType.DENSE_PARAGRAPH: PromptType.REPAIR_DENSE_PARAGRAPH,
            PromptType.TABLE: PromptType.REPAIR_TABLE,
            PromptType.EQUATION: PromptType.REPAIR_EQUATION,
        }
        return mapping.get(prompt_type)
