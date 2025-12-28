"""
Wrapper for shared index_paper implementation.
"""
from backend.core.library import index_paper as index_paper_impl


def index_paper(paper_id: int):
    return index_paper_impl(paper_id)
