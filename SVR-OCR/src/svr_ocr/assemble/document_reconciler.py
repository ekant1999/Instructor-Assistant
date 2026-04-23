from __future__ import annotations

from abc import ABC, abstractmethod

from ..contracts import DocumentMarkdownResult, PageMarkdownWithProvenance


class DocumentReconciler(ABC):
    @abstractmethod
    def reconcile(self, pages: list[PageMarkdownWithProvenance]) -> DocumentMarkdownResult:
        raise NotImplementedError


class SimpleDocumentReconciler(DocumentReconciler):
    def reconcile(self, pages: list[PageMarkdownWithProvenance]) -> DocumentMarkdownResult:
        markdown = "\n\n".join(page.markdown for page in pages if page.markdown.strip())
        diagnostics = {
            "page_count": len(pages),
            "non_empty_pages": sum(1 for page in pages if page.markdown.strip()),
        }
        return DocumentMarkdownResult(markdown=markdown, pages=pages, diagnostics=diagnostics)
