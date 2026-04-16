# olmOCR-Bench Reproduction Workspace

This workspace packages the exact command-line paths needed to reproduce the paper's `olmOCR-Bench` experiments from this repository.

It supports four candidates:

- `qwen_structured`
- `qwen_structured_post`
- `svr_ocr_full`
- `olmocr2`

That is enough to verify the main backend claim in the paper:

- direct general-purpose Qwen baseline
- post-processed Qwen baseline
- `SVR-OCR-Full`
- specialized `olmOCR-2`

## What this workspace does

It gives you:

- a dedicated Python environment setup script
- a single CLI entrypoint: `scripts/benchctl`
- official `olmocr.bench.convert` and `olmocr.bench.benchmark` wrappers
- the `SVR-OCR` bench runner wrapper
- deterministic post-processing for `qwen_structured_post`
- empty-output cleanup
- benchmark summary/compare commands

## Layout

- `scripts/setup_workspace.sh`: create the workspace venv and install dependencies
- `scripts/benchctl`: wrapper around the Python CLI
- `tools/experiment.py`: main CLI implementation
- `.env.example`: endpoint and path template
- `requirements.txt`: Python packages needed by the workspace

## Prerequisites

You need:

1. `python3`
2. Poppler tools:
   - `pdfinfo`
   - `pdftoppm`
3. network access for:
   - installing `olmocr`
   - downloading `olmOCR-Bench`
   - calling the configured OCR endpoints

On macOS:

```bash
brew install poppler
```

## Setup

From the repository root:

```bash
./olmocr_bench_workspace/scripts/setup_workspace.sh
cp olmocr_bench_workspace/.env.example olmocr_bench_workspace/.env
```

Then edit `olmocr_bench_workspace/.env`.

Minimum variables to fill:

```bash
QWEN_SERVER=...
QWEN_API_KEY=...
OLMOCR_SERVER=...
OLMOCR_API_KEY=...
```

Defaults already match the paper:

- `QWEN_MODEL=qwen3-vl-plus`
- `OLMOCR_MODEL=allenai/olmOCR-2-7B-1025-FP8`
- candidate names:
  - `qwen_structured`
  - `qwen_structured_post`
  - `svr_ocr_full`
  - `olmocr2`

## Download the benchmark data

Default download location:

- `olmocr_bench_workspace/data/olmOCR-bench/bench_data`

Run:

```bash
./olmocr_bench_workspace/scripts/benchctl download-bench-data
```

If the downloaded layout differs, set `BENCH_DATA_DIR` in `.env`.

## Validate the workspace

Run:

```bash
./olmocr_bench_workspace/scripts/benchctl validate
```

This checks:

- `SVR-OCR` source path
- `olmocr` Python import
- `pdfinfo`
- `pdftoppm`
- benchmark paths

## Reproduce the paper candidates

### 1. Direct Qwen structured baseline

```bash
./olmocr_bench_workspace/scripts/benchctl convert-qwen-structured --parallel 1
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured
./olmocr_bench_workspace/scripts/benchctl summarize --candidate qwen_structured
```

### 2. Qwen structured + deterministic post-processing

This copies `qwen_structured` into `qwen_structured_post` and applies the deterministic cleanup pass described in the paper.

```bash
./olmocr_bench_workspace/scripts/benchctl postprocess-qwen --force
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured_post
./olmocr_bench_workspace/scripts/benchctl summarize --candidate qwen_structured_post
```

### 3. Specialized `olmOCR-2`

```bash
./olmocr_bench_workspace/scripts/benchctl convert-olmocr2 --parallel 1
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate olmocr2
./olmocr_bench_workspace/scripts/benchctl summarize --candidate olmocr2
```

### 4. `SVR-OCR-Full`

Recommended paper-like settings:

```bash
./olmocr_bench_workspace/scripts/benchctl convert-svr --parallel 4 --target-longest-image-dim 1024
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate svr_ocr_full
./olmocr_bench_workspace/scripts/benchctl summarize --candidate svr_ocr_full
```

## Compare all reproduced results

Once the benchmark stdout files exist in `olmocr_bench_workspace/results`, run:

```bash
./olmocr_bench_workspace/scripts/benchctl compare
```

That prints one line per candidate with:

- average score
- confidence interval half-width
- failed test count
- empty markdown file count

## Empty-file cleanup and resume

Count empty candidate outputs:

```bash
./olmocr_bench_workspace/scripts/benchctl clean-empty --candidate svr_ocr_full
```

Delete empty candidate outputs before a resume run:

```bash
./olmocr_bench_workspace/scripts/benchctl clean-empty --candidate svr_ocr_full --delete
```

Then rerun the same convert command without `--force`.

That lets the runner skip good outputs and regenerate only missing pages.

## Notes on the post-processing baseline

`qwen_structured_post` is implemented here as a deterministic cleanup pass over the `qwen_structured` page outputs. The implementation follows the paper-level recipe:

1. preserve YAML front matter when present
2. remove obvious page-number/header/footer lines
3. normalize heading syntax
4. remove consecutive duplicate lines/headings
5. remove empty headings
6. normalize figure/table placeholder syntax
7. preserve one-file-per-page benchmark layout

This is intentionally simple and transparent. The workspace keeps the recipe in source code so the claimed comparison is inspectable.

## Expected paper-level outcomes

The paper reports:

- `qwen_structured`: `50.0% ± 1.2%`
- `qwen_structured_post`: `52.3% ± 1.2%`
- `svr_ocr_full`: `72.8% ± 1.1%`
- `olmocr2`: `74.7% ± 1.0%`

You should not expect bit-for-bit identical results if:

- endpoint behavior changes
- model providers update the backend
- the benchmark dataset changes
- retry policy differs

But this workspace makes the experimental procedure itself explicit and reproducible.

## Main commands summary

```bash
./olmocr_bench_workspace/scripts/setup_workspace.sh
./olmocr_bench_workspace/scripts/benchctl validate
./olmocr_bench_workspace/scripts/benchctl download-bench-data

./olmocr_bench_workspace/scripts/benchctl convert-qwen-structured --parallel 1
./olmocr_bench_workspace/scripts/benchctl postprocess-qwen --force
./olmocr_bench_workspace/scripts/benchctl convert-olmocr2 --parallel 1
./olmocr_bench_workspace/scripts/benchctl convert-svr --parallel 4 --target-longest-image-dim 1024

./olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured_post
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate olmocr2
./olmocr_bench_workspace/scripts/benchctl benchmark --candidate svr_ocr_full

./olmocr_bench_workspace/scripts/benchctl compare
```
