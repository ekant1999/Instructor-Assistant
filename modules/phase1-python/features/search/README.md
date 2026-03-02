# Search Modules

Files:
- `src/ia_phase1/search_keyword.py`
- `src/ia_phase1/search_hybrid.py`
- `src/ia_phase1/search_context.py`

## What is modularized

- Keyword search over SQLite FTS/LIKE tables (`papers`, `sections`, `notes`, `summaries`).
- Hybrid retrieval helpers for pgvector similarity + PostgreSQL full-text fusion (RRF).
- Section hit localization helpers (query tokenization, best block selection, snippet building).

## APIs

- `search_keyword.py`
  - `configure_connection_factory(factory)`
  - `search_papers(...)`
  - `search_sections(...)`
  - `search_notes(...)`
  - `search_summaries(...)`
  - `search_all(...)`
- `search_hybrid.py`
  - `full_text_search(...)`
  - `reciprocal_rank_fusion(...)`
  - `hybrid_search(...)`
  - `search_with_reranking(...)`
- `search_context.py`
  - `query_tokens(...)`
  - `select_block_for_query(...)`
  - `build_match_snippet(...)`
  - `pgvector_score(...)`

## Minimal usage

```python
from ia_phase1.search_keyword import configure_connection_factory, search_sections

configure_connection_factory(get_conn)  # app-provided SQLite connection factory
rows = search_sections("sequential planning", search_type="keyword", paper_ids=[42], limit=20)
```

```python
from ia_phase1.search_context import query_tokens, build_match_snippet

tokens = query_tokens("sequential planning process")
snippet = build_match_snippet("sequential planning process", tokens, long_text)
```
