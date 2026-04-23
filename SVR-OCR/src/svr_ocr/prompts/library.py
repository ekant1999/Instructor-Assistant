from __future__ import annotations

from pathlib import Path

from ..contracts import PromptType
from ..exceptions import PromptResolutionError


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class PromptLibrary:
    FILES = {
        PromptType.HEADING: "heading.txt",
        PromptType.PARAGRAPH: "paragraph.txt",
        PromptType.DENSE_PARAGRAPH: "dense_paragraph.txt",
        PromptType.TABLE: "table.txt",
        PromptType.EQUATION: "equation.txt",
        PromptType.CAPTION: "caption.txt",
        PromptType.FOOTNOTE: "footnote.txt",
        PromptType.REFERENCE: "reference.txt",
        PromptType.HEADER_FOOTER: "header_footer.txt",
        PromptType.REPAIR_PARAGRAPH: "repair_paragraph.txt",
        PromptType.REPAIR_DENSE_PARAGRAPH: "repair_dense_paragraph.txt",
        PromptType.REPAIR_TABLE: "repair_table.txt",
        PromptType.REPAIR_EQUATION: "repair_equation.txt",
        PromptType.REPAIR_HEADER_FOOTER: "repair_header_footer.txt",
    }

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else Path(__file__).parent

    def get_template(self, prompt_type: PromptType) -> str:
        rel = self.FILES.get(prompt_type)
        if rel is None:
            raise PromptResolutionError(f"No template registered for prompt type: {prompt_type}")
        path = self.root / rel
        if not path.exists():
            raise PromptResolutionError(f"Prompt template missing: {path}")
        return path.read_text().strip()

    def render(self, prompt_type: PromptType, **kwargs: object) -> str:
        template = self.get_template(prompt_type)
        return template.format_map(_SafeDict({key: str(value) for key, value in kwargs.items()}))
