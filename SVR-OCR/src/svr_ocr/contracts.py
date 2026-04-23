from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    EQUATION = "equation"
    FIGURE = "figure"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    REFERENCE = "reference"
    HEADER_FOOTER = "header_footer"
    UNKNOWN = "unknown"


class PromptType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    DENSE_PARAGRAPH = "dense_paragraph"
    TABLE = "table"
    EQUATION = "equation"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    REFERENCE = "reference"
    HEADER_FOOTER = "header_footer"
    REPAIR_PARAGRAPH = "repair_paragraph"
    REPAIR_DENSE_PARAGRAPH = "repair_dense_paragraph"
    REPAIR_TABLE = "repair_table"
    REPAIR_EQUATION = "repair_equation"
    REPAIR_HEADER_FOOTER = "repair_header_footer"


class VerificationStatus(str, Enum):
    ACCEPTED = "accepted"
    REPAIR = "repair"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def expanded(self, margin: float, page_width: float, page_height: float) -> "BoundingBox":
        return BoundingBox(
            x0=max(0.0, self.x0 - margin),
            y0=max(0.0, self.y0 - margin),
            x1=min(page_width, self.x1 + margin),
            y1=min(page_height, self.y1 + margin),
        )


@dataclass
class PageImageBundle:
    page_id: str
    image_path: str
    width: int
    height: int
    dpi: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BlockNode:
    block_id: str
    bbox: BoundingBox
    block_type: BlockType
    confidence: float = 0.0
    difficulty: float = 0.0
    text_density: float = 0.0
    source_text: str | None = None
    column_id: int | None = None
    neighbors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutGraph:
    page_id: str
    page_size: tuple[int, int]
    blocks: list[BlockNode]
    reading_order_edges: list[tuple[str, str]] = field(default_factory=list)

    def ordered_blocks(self) -> list[BlockNode]:
        block_by_id = {block.block_id: block for block in self.blocks}
        explicit_ranks: dict[str, int] = {}
        for rank, block in enumerate(self.blocks):
            explicit = block.metadata.get("reading_order")
            if explicit is not None:
                explicit_ranks[block.block_id] = int(explicit)
            else:
                explicit_ranks[block.block_id] = rank
        return sorted(
            self.blocks,
            key=lambda block: (
                explicit_ranks.get(block.block_id, 10**9),
                block.column_id if block.column_id is not None else 10**6,
                block.bbox.y0,
                block.bbox.x0,
            ),
        )


@dataclass
class CropRequest:
    page_id: str
    block_id: str
    bbox: BoundingBox
    scale: float
    image_path: str
    context_margin: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RefinementDecision:
    block_id: str
    prompt_type: PromptType
    crop_scale: float = 1.0
    num_candidates: int = 1
    repair_budget: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass
class RefinementPlan:
    page_id: str
    decisions: list[RefinementDecision] = field(default_factory=list)

    def by_block_id(self) -> dict[str, RefinementDecision]:
        return {decision.block_id: decision for decision in self.decisions}


@dataclass
class GenerationMetadata:
    model: str = "unknown"
    prompt_type: PromptType | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationBreakdown:
    renderable: bool = False
    render_score: float = 0.0
    structure_score: float = 0.0
    type_consistency_score: float = 0.0
    syntax_validity_score: float = 0.0
    neighbor_consistency_score: float = 0.0
    final_score: float = 0.0
    emit: bool = True
    drop_reason: str | None = None
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class BlockCandidate:
    page_id: str
    block_id: str
    candidate_id: str
    block_type: BlockType
    prompt_type: PromptType
    content: str
    raw_model_output: str
    syntax_valid: bool = True
    generation_metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    is_repair: bool = False


@dataclass
class VerifiedBlockCandidate:
    candidate: BlockCandidate
    verification: VerificationBreakdown


@dataclass
class SelectedBlock:
    block_id: str
    candidate: BlockCandidate
    verification: VerificationBreakdown
    repair_count: int = 0
    degraded: bool = False


@dataclass
class PageMarkdownWithProvenance:
    page_id: str
    markdown: str
    ordered_blocks: list[str]
    provenance: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class DocumentMarkdownResult:
    markdown: str
    pages: list[PageMarkdownWithProvenance]
    diagnostics: dict[str, Any] = field(default_factory=dict)
