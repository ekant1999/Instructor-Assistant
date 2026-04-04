from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

DocumentBlockKind = Literal["text", "math", "code", "asset", "page_marker", "separator"]
PageBlockKind = Literal["text", "asset"]


@dataclass(slots=True)
class DocumentBlock:
    kind: DocumentBlockKind
    text: str
    page_num: int = 0


@dataclass(slots=True)
class DocumentSection:
    title: str
    level: int
    page_start: int = 0
    page_end: int = 0
    blocks: List[DocumentBlock] = field(default_factory=list)

    def has_meaningful_content(self) -> bool:
        for block in self.blocks:
            if block.kind not in {"text", "math", "code"}:
                continue
            if block.text.strip():
                return True
        return False

    def has_renderable_content(self) -> bool:
        for block in self.blocks:
            if block.kind in {"page_marker", "separator"}:
                continue
            if block.text.strip():
                return True
        return False


@dataclass(slots=True)
class DocumentModel:
    title: Optional[str] = None
    front_matter: List[DocumentBlock] = field(default_factory=list)
    sections: List[DocumentSection] = field(default_factory=list)


@dataclass(slots=True)
class DocumentOutlineEntry:
    title: str
    level: int
    page_num: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass(slots=True)
class PageBlock:
    kind: PageBlockKind
    text: str
    bbox: Tuple[float, float, float, float]
    page_num: int
    page_mode: str


@dataclass(slots=True)
class PageModel:
    page_num: int
    page_mode: str
    width: float
    height: float
    blocks: List[PageBlock] = field(default_factory=list)
