# Markdown Evaluation

This workspace benchmarks PDF-to-Markdown extraction quality across two systems:

- `ia_phase1`: the current project pipeline under `modules/phase1-python/src/ia_phase1`
- `ocr_agent`: the alternative hybrid extractor added under `ocr_agent/`

The benchmark is designed to answer three questions:

1. Which system is more faithful to the source PDF on different document types?
2. Which failure modes dominate each system?
3. Which architectural ideas should later be integrated into the project codebase?

## Workspace layout

- `metadata.jsonl`: benchmark corpus manifest
- `gold/docs/`: per-document gold annotations for structure, anchors, and assets
- `outputs/`: raw system outputs
- `normalized/`: common normalized schema derived from raw markdown outputs
- `runs/`: raw run manifests and score traces
- `reports/`: aggregate benchmark reports
- `scripts/`: corpus, runner, normalization, and scoring helpers
- `tests/`: unit tests for normalization/scoring

## Benchmark philosophy

This benchmark does not compare raw markdown strings directly. Instead it:

1. runs both extraction systems
2. normalizes their outputs into a common JSON schema
3. scores them against gold annotations when gold exists
4. always reports intrinsic markdown quality metrics even when gold is missing

That makes it useful in two modes:

- `gold-ready mode`: compare systems against curated truth
- `bootstrap mode`: compare structural quality and failure counts before full gold is finished

## Gold annotation shape

Each gold document file in `gold/docs/<doc_id>.json` is expected to look like this:

```json
{
  "doc_id": "p119",
  "title": "VLA-OPD: ...",
  "validated": false,
  "headings": [
    {"level": 2, "text": "Preliminaries"},
    {"level": 3, "text": "Online RL with Sparse Outcome Rewards"}
  ],
  "section_anchors": [
    {
      "text": "However, despite its provenance",
      "expected_section": "Online RL with Sparse Outcome Rewards",
      "position": "end"
    }
  ],
  "figures": [
    {"number": 1, "caption_contains": ["..."]}
  ],
  "tables": [
    {"number": 2, "caption_contains": ["..."]}
  ]
}
```

Important:

- bootstrapped templates are created with `"validated": false`
- the scorer only uses gold annotations when `"validated": true`
- this prevents draft templates from being mistaken for real ground truth

## Core metrics

With gold available:

- heading precision / recall / F1
- heading order score
- section-anchor recall
- section-anchor assignment accuracy
- figure recall
- table recall

Without gold:

- duplicate heading count
- empty section count
- consecutive heading-run count
- suspicious heading count
- duplicate figure-caption count
- duplicate table-caption count
- section count
- runtime

## Commands

Run both systems, normalize outputs, and score them:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/run_benchmark.py \
  --systems ia_phase1 ocr_agent \
  --bootstrap-gold \
  --timeout-seconds 60
```

Run only the project pipeline:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/run_ia_phase1.py
```

Run only the hybrid extractor:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/run_ocr_agent.py \
  --timeout-seconds 60
```

Normalize previously generated outputs:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/normalize_outputs.py
```

Score normalized outputs:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/score_outputs.py
```

Bootstrap gold annotation templates from current metadata and normalized headings:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/bootstrap_gold_templates.py
```

Render a markdown index for manual gold curation:

```bash
backend/.webenv/bin/python markdown_evaluation/scripts/render_curation_index.py
```

## Current pilot corpus

The seeded corpus uses the current local regression papers:

- `110`
- `112`
- `114`
- `115`
- `116`
- `118`
- `119`
- `120`

These are intentionally difficult and cover multiple layout / failure categories.
