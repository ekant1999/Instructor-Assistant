# PGVECTOR + PDF BBOX + WEB/GDOC CHANGES (Summary)

This is a quick summary of the recent changes related to pgvector search, PDF bbox/highlighting, and web/Google Docs ingestion.

## Pgvector Search + Ingestion
- Switched RAG retrieval to pgvector (embedding + hybrid search).
- Hybrid search uses pgvector similarity + Postgres/SQLite keyword search.
- Pgvector ingestion writes text blocks with embeddings, metadata, and bbox when available.
- Per-event-loop asyncpg pools; vector codec registered for pgvector.
- Added safeguards for UTF-8/NULL bytes and timestamp normalization.

Key files:
- `backend/rag/pgvector_store.py`
- `backend/rag/ingest_pgvector.py`
- `backend/rag/query_pgvector.py`
- `backend/core/postgres.py`
- `backend/core/hybrid_search.py`
- `backend/main.py`

## PDF BBox + Highlighting
- PDF text extraction uses PyMuPDF block bboxes.
- Frontend uses PDF.js and highlights exact text match when possible.
- If exact match is not found, it falls back to bbox highlighting.
- Bbox coordinates are Y-flipped to match PDF.js viewport.
- Improved snippet selection so the highlight aligns with the query.

Key files:
- `backend/core/pdf.py`
- `backend/main.py`
- `client/src/library/PdfPreview.tsx`
- `client/src/library/EnhancedLibraryPage.tsx`

## Web + Google Docs Ingestion
- Any URL can be added; if no PDF is found, it falls back to web extraction.
- Google Docs links are supported via public export-to-text (and title from HTML when available).
- Extracted web text is chunked and stored in SQLite sections, then embedded into pgvector.
- Web docs do not have PDF previews but are fully searchable and usable in RAG.

Key files:
- `backend/core/web.py`
- `backend/core/library.py`
- `backend/rag/ingest_pgvector.py`
- `backend/main.py`

## Web Preview UI + Search Highlighting
- Added a Web preview tab for non-PDF documents.
- Highlights the matched snippet directly in the web text.
- Search results are cached separately so clearing search restores full chunks.
- Highlight state resets when search is cleared.
- Paper list icons show PDF vs WEB at a glance.

Key files:
- `client/src/library/WebPreview.tsx`
- `client/src/library/EnhancedLibraryPage.tsx`
- `client/src/library/EnhancedPaperList.tsx`
- `client/src/library/PaperList.tsx`
