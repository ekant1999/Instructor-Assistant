"""
Wrapper for shared save_note implementation.
"""
from typing import Optional
from backend.core.library import save_note as save_note_impl


def save_note(paper_id: int, body: str, title: Optional[str] = None):
    return save_note_impl(paper_id, body, title)
