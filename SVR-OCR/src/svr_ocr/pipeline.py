from __future__ import annotations

from dataclasses import dataclass

from .assemble.document_reconciler import DocumentReconciler, SimpleDocumentReconciler
from .assemble.page_assembler import MarkdownPageAssembler, PageAssembler
from .config import EndpointConfig, SVROCRConfig
from .contracts import (
    BlockCandidate,
    BlockNode,
    BlockType,
    DocumentMarkdownResult,
    GenerationMetadata,
    LayoutGraph,
    PageImageBundle,
    PageMarkdownWithProvenance,
    PromptType,
    SelectedBlock,
    VerificationBreakdown,
    VerifiedBlockCandidate,
)
from .crops.crop_manager import CropManager, SimpleCropManager
from .crops.refinement_policy import TypedRefinementPlanner
from .layout.graph_builder import HeuristicLayoutGraphBuilder, LayoutGraphBuilder
from .prompts.library import PromptLibrary
from .repair.repair_runner import RepairRunner, SimpleRepairRunner
from .transcribe import (
    BlockTranscriber,
    CandidateStore,
    InMemoryCandidateStore,
    OpenAICompatibleBlockTranscriber,
    PassthroughBlockTranscriber,
    TranscriptionRequest,
)
from .verify import (
    EquationBlockVerifier,
    HeaderFooterBlockVerifier,
    TableBlockVerifier,
    TextBlockVerifier,
    VerifierRouter,
)


@dataclass
class SVROCRPipeline:
    config: SVROCRConfig
    graph_builder: LayoutGraphBuilder
    refinement_planner: TypedRefinementPlanner
    crop_manager: CropManager
    prompt_library: PromptLibrary
    transcriber: BlockTranscriber
    candidate_store: CandidateStore
    verifier: VerifierRouter
    repair_runner: RepairRunner
    page_assembler: PageAssembler
    document_reconciler: DocumentReconciler

    def process_document(self, pages: list[PageImageBundle]) -> DocumentMarkdownResult:
        page_outputs = [self.process_page(page) for page in pages]
        return self.document_reconciler.reconcile(page_outputs)

    def process_page(self, page: PageImageBundle) -> PageMarkdownWithProvenance:
        graph = self.graph_builder.build(page)
        plan = self.refinement_planner.plan(page, graph)
        crop_requests = self.crop_manager.build_requests(page, graph, plan)
        decision_by_id = plan.by_block_id()
        selected_blocks: dict[str, SelectedBlock] = {}

        for block in graph.ordered_blocks():
            decision = decision_by_id.get(block.block_id)
            if decision is None:
                selected_blocks[block.block_id] = self._passthrough_block(page, block)
                continue

            prompt_text = self.prompt_library.render(
                decision.prompt_type,
                block_type=block.block_type.value,
                source_text=block.source_text or "",
                position_band=block.metadata.get("position_band", ""),
                page_num=block.metadata.get("page_num", page.metadata.get("page_num", "")),
                drop_marker=self.config.header_footer.drop_marker,
            )
            request = TranscriptionRequest(
                page=page,
                block=block,
                crop=crop_requests.get(block.block_id),
                prompt_type=decision.prompt_type,
                prompt_text=prompt_text,
                num_candidates=decision.num_candidates,
            )
            candidates = self.transcriber.generate_candidates(request)
            self.candidate_store.save(block.block_id, candidates)
            verified = [self.verifier.verify(block, candidate, graph) for candidate in candidates]
            best = self._best_verified_candidate(verified)
            repair_count = 0

            while (
                best.verification.final_score < self.config.thresholds.repair_score
                and repair_count < decision.repair_budget
            ):
                repaired_candidates = self.repair_runner.attempt_repair(
                    page=page,
                    block=block,
                    crop=crop_requests.get(block.block_id),
                    decision=decision,
                    failed=best,
                    transcriber=self.transcriber,
                    prompt_library=self.prompt_library,
                    candidate_store=self.candidate_store,
                )
                if not repaired_candidates:
                    break
                repaired_verified = [
                    self.verifier.verify(block, candidate, graph)
                    for candidate in repaired_candidates
                ]
                verified.extend(repaired_verified)
                best = self._best_verified_candidate(verified)
                repair_count += 1

            degraded = best.verification.final_score < self.config.thresholds.accept_score
            selected_blocks[block.block_id] = SelectedBlock(
                block_id=block.block_id,
                candidate=best.candidate,
                verification=best.verification,
                repair_count=repair_count,
                degraded=degraded,
            )

        return self.page_assembler.assemble(page, graph, selected_blocks)

    def _best_verified_candidate(
        self,
        verified_candidates: list[VerifiedBlockCandidate],
    ) -> VerifiedBlockCandidate:
        return max(
            verified_candidates,
            key=lambda item: (
                item.verification.final_score,
                item.verification.render_score,
                item.verification.structure_score,
            ),
        )

    def _passthrough_block(self, page: PageImageBundle, block: BlockNode) -> SelectedBlock:
        content = (block.source_text or "").strip()
        if not content and block.block_type == BlockType.HEADING:
            content = "Untitled Heading"
        candidate = BlockCandidate(
            page_id=page.page_id,
            block_id=block.block_id,
            candidate_id=f"{block.block_id}_seed",
            block_type=block.block_type,
            prompt_type=self._seed_prompt_type(block.block_type),
            content=content,
            raw_model_output=content,
            syntax_valid=True,
            generation_metadata=GenerationMetadata(
                model=self.config.default_model_name,
                prompt_type=self._seed_prompt_type(block.block_type),
                extra={"seed": True},
            ),
        )
        verification = VerificationBreakdown(
            renderable=bool(content),
            render_score=1.0 if content else 0.0,
            structure_score=1.0 if content else 0.0,
            type_consistency_score=1.0 if content else 0.0,
            syntax_validity_score=1.0,
            neighbor_consistency_score=1.0 if content else 0.0,
            final_score=1.0 if content else 0.0,
            failure_reasons=[] if content else ["empty_seed_block"],
        )
        return SelectedBlock(
            block_id=block.block_id,
            candidate=candidate,
            verification=verification,
            repair_count=0,
            degraded=not bool(content),
        )

    def _seed_prompt_type(self, block_type: BlockType) -> PromptType:
        mapping = {
            BlockType.HEADING: PromptType.HEADING,
            BlockType.TABLE: PromptType.TABLE,
            BlockType.EQUATION: PromptType.EQUATION,
            BlockType.CAPTION: PromptType.CAPTION,
            BlockType.FOOTNOTE: PromptType.FOOTNOTE,
            BlockType.REFERENCE: PromptType.REFERENCE,
            BlockType.HEADER_FOOTER: PromptType.HEADER_FOOTER,
        }
        return mapping.get(block_type, PromptType.PARAGRAPH)


def build_default_pipeline(config: SVROCRConfig | None = None) -> SVROCRPipeline:
    config = config or SVROCRConfig()
    return _build_pipeline(
        config=config,
        transcriber=PassthroughBlockTranscriber(model_name=config.default_model_name),
    )


def build_openai_compatible_pipeline(
    config: SVROCRConfig | None = None,
    endpoint: EndpointConfig | None = None,
) -> SVROCRPipeline:
    config = config or SVROCRConfig()
    endpoint = endpoint or config.endpoint or EndpointConfig.from_env()
    if config.default_model_name == "svr-ocr-scaffold" and endpoint.model_name:
        config.default_model_name = endpoint.model_name
    return _build_pipeline(
        config=config,
        transcriber=OpenAICompatibleBlockTranscriber(endpoint=endpoint),
    )


def _build_pipeline(
    *,
    config: SVROCRConfig,
    transcriber: BlockTranscriber,
) -> SVROCRPipeline:
    return SVROCRPipeline(
        config=config,
        graph_builder=HeuristicLayoutGraphBuilder(),
        refinement_planner=TypedRefinementPlanner(config),
        crop_manager=SimpleCropManager(context_margin=config.crop_context_margin),
        prompt_library=PromptLibrary(),
        transcriber=transcriber,
        candidate_store=InMemoryCandidateStore(),
        verifier=VerifierRouter(
            text_verifier=TextBlockVerifier(),
            table_verifier=TableBlockVerifier(),
            equation_verifier=EquationBlockVerifier(),
            header_footer_verifier=HeaderFooterBlockVerifier(
                drop_marker=config.header_footer.drop_marker,
            ),
        ),
        repair_runner=SimpleRepairRunner(),
        page_assembler=MarkdownPageAssembler(),
        document_reconciler=SimpleDocumentReconciler(),
    )
