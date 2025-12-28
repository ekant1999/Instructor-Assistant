"""arXiv search and download tools."""
from __future__ import annotations

from typing import Dict, List, Optional

import arxiv

from .utils import safe_path


def arxiv_search(query: str, max_results: int = 5) -> Dict[str, object]:
    """Search arXiv for papers matching a query."""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    papers: List[Dict[str, object]] = []
    for result in search.results():
        papers.append(
            {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "arxiv_id": result.entry_id.split("/")[-1],
                "published": str(result.published),
                "summary": result.summary[:500],
                "pdf_url": result.pdf_url,
            }
        )
    return {"query": query, "papers": papers}


def arxiv_download(arxiv_id: str, output_path: Optional[str] = None) -> Dict[str, object]:
    """Download an arXiv PDF by ID and return metadata + saved path."""
    clean_id = arxiv_id.replace("arxiv:", "").replace("arXiv:", "")
    search = arxiv.Search(id_list=[clean_id])
    paper = next(search.results(), None)
    if not paper:
        raise ValueError(f"Paper {arxiv_id} not found")

    out_path = safe_path(output_path or f"{clean_id}.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    paper.download_pdf(dirpath=str(out_path.parent), filename=out_path.name)

    return {
        "arxiv_id": clean_id,
        "title": paper.title,
        "file_path": str(out_path),
        "pdf_url": paper.pdf_url,
    }

