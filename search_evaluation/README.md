# Search Evaluation

This workspace benchmarks the current unified hybrid library search against a
fixed arXiv PDF corpus.

## What it contains

- `pdfs/`: downloaded arXiv PDFs
- `metadata.jsonl`: corpus manifest with stable benchmark paper IDs
- `queries.jsonl`: benchmark queries only
- `gold.jsonl`: benchmark queries with curated gold labels
- `reviews/`: per-paper review notes used to curate the gold set
- `runs/`: raw benchmark traces
- `reports/`: aggregate reports
- `scripts/`: helpers for fetch, corpus build, review extraction, and benchmark runs
- `state/`: isolated SQLite benchmark database and temporary manifests

## Workflow

1. Download a 20-paper arXiv corpus:

```bash
backend/.webenv/bin/python search_evaluation/scripts/fetch_arxiv_papers.py
```

2. Build the isolated SQLite eval corpus and ingest the same papers into pgvector:

```bash
backend/.webenv/bin/python search_evaluation/scripts/build_eval_corpus.py
```

3. Extract compact review summaries from each PDF for manual curation:

```bash
backend/.webenv/bin/python search_evaluation/scripts/review_papers.py
```

4. Curate `gold.jsonl` and `queries.jsonl`.

5. Run the unified hybrid search benchmark:

```bash
backend/.webenv/bin/python search_evaluation/scripts/run_benchmark.py
```

6. Remove benchmark papers from PostgreSQL after the run:

```bash
backend/.webenv/bin/python search_evaluation/scripts/cleanup_eval_pg.py
```

## Benchmark scope

The current benchmark measures the active search system:

- paper ranking from unified section hits
- within-paper localization via the same section-hit engine

Primary metrics:

- `hit_at_1`
- `hit_at_3`
- `hit_at_5`
- `mrr`
- `no_match_accuracy`
- `page_hit_at_1`
- `section_hit_at_1`
- `latency_ms_{mean,p50,p95}`

## Isolation model

- SQLite corpus lives in `search_evaluation/state/app_eval.db`
- pgvector indexing uses reserved high paper IDs from `metadata.jsonl`
- benchmark runs restrict retrieval to those benchmark paper IDs

This avoids mixing the benchmark with the active library UI while still testing
the real search code path.
