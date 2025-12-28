"""
Wrapper for shared get_paper_chunk implementation.
"""
from backend.core.library import get_paper_chunk as get_paper_chunk_impl


def get_paper_chunk(section_id: int):
    return get_paper_chunk_impl(section_id)
