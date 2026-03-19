# Search Modules

Files:
- `src/ia_phase1/search_keyword.py`
- `src/ia_phase1/search_hybrid.py`
- `src/ia_phase1/search_context.py`
- `src/ia_phase1/search_pipeline.py`
- `examples/example_search_pipeline.py`

## What is modularized

- Keyword search over SQLite FTS/LIKE tables (`papers`, `sections`, `notes`, `summaries`).
- Hybrid retrieval helpers for pgvector similarity + PostgreSQL full-text fusion (RRF).
- Section hit localization helpers (query tokenization, best block selection, snippet building).
- Unified search pipeline helpers for:
  - section-hit merging
  - no-match gating
  - title rescue
  - section-to-paper aggregation
  - post-ranking localization reranking for picking a better page/section hit inside the selected paper

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
- `search_pipeline.py`
  - `configure_connection_factory(factory)`
  - `rrf_score(...)`
  - `token_overlap(...)`
  - `infer_search_section_bucket(...)`
  - `section_bucket_multiplier(...)`
  - `query_token_stats(...)`
  - `infer_localization_query_profile(...)`
  - `infer_localization_section_role(...)`
  - `paper_title_bonus_lookup(...)`
  - `localization_score_for_hit(...)`
  - `rerank_section_hits_for_localization(...)`
  - `search_paper_sections_for_localization(...)`
  - `filter_section_hits_for_query(...)`
  - `filter_aggregated_papers_for_query(...)`
  - `inject_title_only_candidates(...)`
  - `merge_section_hits(...)`
  - `search_section_hits_unified(...)`
  - `aggregate_section_hits_to_papers(...)`

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

```python
from ia_phase1.search_pipeline import (
    configure_connection_factory,
    filter_section_hits_for_query,
    aggregate_section_hits_to_papers,
    search_paper_sections_for_localization,
    search_section_hits_unified,
)

configure_connection_factory(get_conn)

section_hits = search_section_hits_unified(
    "large language model",
    "hybrid",
    keyword_section_hits_fn=keyword_section_hits_fn,
    semantic_section_hits_fn=semantic_section_hits_fn,
    include_text=False,
    max_chars=None,
    limit=100,
)
section_hits = filter_section_hits_for_query("large language model", section_hits)
paper_scores = aggregate_section_hits_to_papers(section_hits)
top_paper_id = max(paper_scores.items(), key=lambda item: item[1]["score"])[0]
localized_hits = search_paper_sections_for_localization(
    "large language model",
    "hybrid",
    paper_id=top_paper_id,
    keyword_section_hits_fn=keyword_section_hits_fn,
    semantic_section_hits_fn=semantic_section_hits_fn,
    include_text=False,
    max_chars=None,
)
```

## Runnable Example

See:
- `modules/phase1-python/examples/example_search_pipeline.py`

Run it:

```bash
cd modules/phase1-python
python examples/example_search_pipeline.py
python examples/example_search_pipeline.py "vision benchmark"
python examples/example_search_pipeline.py "molecule property prediction"
```

Notes:
- the example uses a tiny in-memory SQLite corpus
- keyword retrieval is real SQLite FTS
- semantic retrieval is a toy callback for demonstration only
- replace that callback with your pgvector/embedding retrieval in a real app

## Trace Logging

Enable compact search tracing with:

- `SEARCH_TRACE_ENABLED=true`
- optional `SEARCH_TRACE_MAX_HITS` (default `5`)
- optional `SEARCH_TRACE_TEXT_CHARS` (default `160`)

When enabled, `search_pipeline.py` logs:
- raw unified section hits
- kept vs dropped section hits after query gating
- aggregated paper candidates
- title-only rescues
- final kept paper hits
- localized section hits inside the selected paper

## Module Boundary

- Keep environment-specific retrieval inside the app:
  - SQLite connection ownership
  - pgvector pool/store usage
  - endpoint response shaping
- Move reusable policy into `search_pipeline.py`:
  - ranking formulas
  - bucket penalties
  - query gating
  - title rescue
  - section-to-paper aggregation
  - post-ranking intra-paper localization reranking

That keeps the package reusable while avoiding hard-coupling it to one backend runtime.
