from __future__ import annotations

from ..contracts import BlockType

TEXTUAL_TYPES = {
    BlockType.TITLE,
    BlockType.HEADING,
    BlockType.PARAGRAPH,
    BlockType.LIST,
    BlockType.CAPTION,
    BlockType.FOOTNOTE,
    BlockType.REFERENCE,
}

STRUCTURE_CRITICAL_TYPES = {
    BlockType.TABLE,
    BlockType.EQUATION,
    BlockType.HEADING,
    BlockType.CAPTION,
}
