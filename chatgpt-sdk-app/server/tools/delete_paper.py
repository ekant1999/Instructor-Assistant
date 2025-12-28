"""
Wrapper for shared delete_paper implementation.
"""
from backend.core.library import delete_paper as delete_paper_impl


def delete_paper(paper_id: int):
    return delete_paper_impl(paper_id)
