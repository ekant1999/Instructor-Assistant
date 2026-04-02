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

Run all commands from the **repo root**:

```bash
cd /path/to/Instructor-Assistant
```

If Python cannot resolve `markdown_evaluation.*` imports, prefix commands with `PYTHONPATH=.`.

## End-to-end benchmark workflow

### 1. Add PDFs

Place source PDFs under `markdown_evaluation/pdfs/`, for example:

```text
markdown_evaluation/pdfs/
```

### 2. Register each PDF in `metadata.jsonl`

Add one JSONL row per PDF:

```json
{"doc_id":"d001","title":"Sample Document","pdf_path":"markdown_evaluation/pdfs/sample.pdf","layout_type":"one_column","doc_tags":["born_digital","non_academic"],"notes":"Short description of this document."}
```

Use a unique `doc_id` for each document. `paper_id` is optional.

### 3. Run extraction + normalization + scoring

This runs both systems, rewrites outputs, regenerates normalized JSON, and updates reports:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_benchmark.py \
  --overwrite \
  --ensure-assets
```

Outputs are written to:

- `markdown_evaluation/outputs/`
- `markdown_evaluation/normalized/`
- `markdown_evaluation/reports/summary.md`
- `markdown_evaluation/reports/summary.json`
- `markdown_evaluation/runs/latest_scores.json`

### 4. Bootstrap gold templates for newly added docs

After a first run has produced normalized outputs, create draft gold JSON files:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/bootstrap_gold_templates.py
```

This creates files under `markdown_evaluation/gold/docs/` with:

- headings/assets copied from current normalized outputs as a **draft skeleton**
- empty `section_anchors`
- `"validated": false`

### 5. Manually curate the gold files from the source PDFs

Edit `markdown_evaluation/gold/docs/<doc_id>.json` and verify against the original PDF, not either system output.

Fill/update:

- `headings`
- `section_anchors`
- `figures`
- `tables`
- `notes`

Then set:

```json
"validated": true
```

Suggested manual evidence sources:

```bash
pdftotext -layout markdown_evaluation/pdfs/<file>.pdf /tmp/<doc_id>.txt
pdftoppm -png -f 1 -singlefile markdown_evaluation/pdfs/<file>.pdf /tmp/<doc_id>_p1
```

### 6. Rescore after gold-only edits

If you changed only `gold/docs/*.json`, do **not** rerun extraction or normalization. Just rescore:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_benchmark.py \
  --skip-run \
  --skip-normalize
```

### 7. Rerun after code changes

Use the right rerun mode depending on what changed.

If you changed parser/export code:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_benchmark.py \
  --overwrite \
  --ensure-assets
```

If you changed only normalization logic:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_benchmark.py \
  --skip-run
```

If you changed only scoring logic or gold files:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_benchmark.py \
  --skip-run \
  --skip-normalize
```

### 8. Inspect the reports

Read:

- `markdown_evaluation/reports/summary.md`
- `markdown_evaluation/reports/summary.json`
- `markdown_evaluation/runs/latest_scores.json`

For manual curation status, regenerate and inspect:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/render_curation_index.py
```

Then open:

- `markdown_evaluation/reports/gold_curation.md`

## Individual helper commands

Run only the project pipeline:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_ia_phase1.py \
  --overwrite \
  --ensure-assets
```

Run only the hybrid extractor:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/run_ocr_agent.py \
  --overwrite \
  --timeout-seconds 180
```

Normalize previously generated outputs:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/normalize_outputs.py
```

Score normalized outputs:

```bash
PYTHONPATH=. backend/.webenv/bin/python markdown_evaluation/scripts/score_outputs.py
```

## Current pilot corpus

The current benchmark corpus includes manually curated academic and non-academic PDFs listed in `metadata.jsonl`, with gold files under `gold/docs/`.
