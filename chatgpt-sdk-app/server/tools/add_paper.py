"""
Wrappers around shared library module to keep existing imports working.
"""
from pathlib import Path
from backend.core.library import add_paper as add_paper_impl, add_local_pdf as add_local_pdf_impl


async def add_paper(input_str: str, source_url: str | None = None):
    return await add_paper_impl(input_str, source_url)


def add_local_pdf(title: str | None, pdf_path: str | Path, source_url: str | None = None):
    return add_local_pdf_impl(title, pdf_path, source_url)
