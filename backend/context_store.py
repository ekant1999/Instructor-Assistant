from __future__ import annotations

from typing import Dict, List, Optional

from .schemas import QuestionContextUploadResponse

_CONTEXTS: Dict[str, QuestionContextUploadResponse] = {}


def save_context(ctx: QuestionContextUploadResponse) -> None:
    _CONTEXTS[ctx.context_id] = ctx


def list_contexts() -> List[QuestionContextUploadResponse]:
    return list(_CONTEXTS.values())


def get_context(context_id: str) -> Optional[QuestionContextUploadResponse]:
    return _CONTEXTS.get(context_id)


def clear_context(context_id: str) -> None:
    _CONTEXTS.pop(context_id, None)
