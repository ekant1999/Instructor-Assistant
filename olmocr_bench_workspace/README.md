# olmOCR-Bench and NVIDIA Omni Evaluation Workspace

This workspace packages the command-line paths needed to run `olmOCR-Bench` experiments and the NVIDIA Nemotron Omni PDF/audio evaluations used in this project.

It supports the original paper-style OCR candidates:

- `qwen_structured`
- `qwen_structured_post`
- `svr_ocr_full`
- `olmocr2`

It also includes NVIDIA evaluation scripts for:

- PDF/OCR evaluation on `olmOCR-Bench`
- audio transcription evaluation on short Open ASR Leaderboard clips

The NVIDIA model currently configured by default is:

```text
nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
```

## What this workspace does

It gives you:

- a dedicated Python environment setup script
- a single CLI entrypoint: `scripts/benchctl`
- official `olmocr.bench.convert` and `olmocr.bench.benchmark` wrappers
- the `SVR-OCR` bench runner wrapper
- deterministic post-processing for `qwen_structured_post`
- empty-output cleanup
- benchmark summary/compare commands
- NVIDIA PDF/OCR demo and evaluation runners
- NVIDIA audio transcription runner and WER summarizer

## Layout

- `scripts/setup_workspace.sh`: create the workspace venv and install dependencies
- `scripts/benchctl`: wrapper around the Python CLI
- `scripts/run_nvidia_pdf_eval.sh`: NVIDIA PDF/OCR conversion, benchmark, and summary
- `scripts/run_nvidia_audio_eval.sh`: NVIDIA audio transcription evaluation and summary
- `scripts/run_nvidia_full_convert.sh`: NVIDIA PDF/OCR conversion only
- `scripts/run_nvidia_open_asr.py`: NVIDIA audio transcription runner
- `scripts/summarize_nvidia_asr.py`: audio prediction analysis and WER summary
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
   - downloading Open ASR Leaderboard audio samples from Hugging Face
   - calling the configured OCR endpoints

On macOS:

```bash
brew install poppler
```

## Setup

From the repository root:

```bash
cd "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA"

Instructor-Assistant/olmocr_bench_workspace/scripts/setup_workspace.sh
cp Instructor-Assistant/olmocr_bench_workspace/.env.example Instructor-Assistant/olmocr_bench_workspace/.env
```

Then edit:

```text
Instructor-Assistant/olmocr_bench_workspace/.env
```

Minimum variables for the original paper-style OCR candidates:

```bash
QWEN_SERVER=...
QWEN_API_KEY=...
OLMOCR_SERVER=...
OLMOCR_API_KEY=...
```

Minimum variables for NVIDIA PDF/audio evaluation:

```bash
export NVIDIA_SERVER="https://integrate.api.nvidia.com/v1"
export NVIDIA_MODEL="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
export NVIDIA_API_KEY="..."
```

Optional audio controls can also go in `.env`:

```bash
export AUDIO_SAMPLES_PER_DATASET=50
export AUDIO_MAX_DURATION=3
export AUDIO_MAX_TOKENS=128
export AUDIO_PROMPT_STYLE=strict
```

Do not commit `.env`; it contains API keys.

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

- `Instructor-Assistant/olmocr_bench_workspace/data/olmOCR-bench/bench_data`

Run:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl download-bench-data
```

If the downloaded layout differs, set `BENCH_DATA_DIR` in `.env`.

## Validate the workspace

Run:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl validate
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
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl convert-qwen-structured --parallel 1
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl summarize --candidate qwen_structured
```

### 2. Qwen structured + deterministic post-processing

This copies `qwen_structured` into `qwen_structured_post` and applies the deterministic cleanup pass described in the paper.

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl postprocess-qwen --force
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured_post
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl summarize --candidate qwen_structured_post
```

### 3. Specialized `olmOCR-2`

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl convert-olmocr2 --parallel 1
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate olmocr2
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl summarize --candidate olmocr2
```

### 4. `SVR-OCR-Full`

Recommended paper-like settings:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl convert-svr --parallel 4 --target-longest-image-dim 1024
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate svr_ocr_full
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl summarize --candidate svr_ocr_full
```

## NVIDIA PDF/OCR eval

The NVIDIA PDF evaluation uses the patched local `olmocr` checkout under:

```text
ocr-paper-work/olmocr
```

The one-command PDF runner does:

1. NVIDIA API preflight
2. PDF-to-Markdown conversion with NVIDIA Omni
3. `olmOCR-Bench` scoring
4. compact text summary

Run the full conversion and benchmark:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_pdf_eval.sh
```

Useful overrides:

```bash
export NVIDIA_CANDIDATE=nemotron_omni_nvidia_ocr
export NVIDIA_PARALLEL=1
export NVIDIA_PROMPT_TEMPLATE=nvidia_ocr
export NVIDIA_BOOTSTRAP_SAMPLES=200
export NVIDIA_MAX_REPORTS=20
```

To test the more structured NVIDIA OCR prompt before a full run:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_structured_quality5.sh
```

To run the full benchmark with the structured prompt as a separate candidate:

```bash
NVIDIA_CANDIDATE=nemotron_omni_nvidia_ocr_structured \
NVIDIA_PROMPT_TEMPLATE=nvidia_ocr_structured \
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_pdf_eval.sh
```

NVIDIA PDF conversion Markdown files are stored under the candidate directory:

```text
Instructor-Assistant/olmocr_bench_workspace/data/olmOCR-bench/bench_data/nemotron_omni_nvidia_ocr
```

NVIDIA PDF benchmark reports are stored in:

```text
Instructor-Assistant/olmocr_bench_workspace/results/nemotron_omni_nvidia_ocr_report.html
Instructor-Assistant/olmocr_bench_workspace/results/nemotron_omni_nvidia_ocr_report.md
Instructor-Assistant/olmocr_bench_workspace/results/nemotron_omni_nvidia_ocr_stdout.txt
Instructor-Assistant/olmocr_bench_workspace/results/nemotron_omni_nvidia_ocr_failed.jsonl
```

The conversion-only script is still available:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_full_convert.sh
```

## NVIDIA audio eval

The audio evaluation uses short clips from:

```text
hf-audio/open-asr-leaderboard
```

It sends inline audio to NVIDIA Omni, writes predictions, and computes WER.

Run the default audio evaluation:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_audio_eval.sh
```

Default settings:

```text
datasets:
  librispeech:test.clean
  librispeech:test.other
  common_voice:test
  ami:test
  earnings22:test

samples per dataset spec: 50
requested total samples: 250
max clip duration: 3 seconds
max output tokens: 128
prompt style: strict
```

Change the sample count with `AUDIO_SAMPLES_PER_DATASET`.

```bash
# 10 requested samples total: 2 from each of 5 dataset specs
AUDIO_SAMPLES_PER_DATASET=2 \
AUDIO_OUTPUT_DIR=Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_demo_short \
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_audio_eval.sh
```

```bash
# 250 requested samples total: 50 from each of 5 dataset specs
AUDIO_SAMPLES_PER_DATASET=50 \
AUDIO_OUTPUT_DIR=Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_strict \
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_audio_eval.sh
```

Audio outputs are written to the configured `AUDIO_OUTPUT_DIR`:

```text
report.md
analysis.md
predictions.jsonl
audio/
```

Previously generated NVIDIA audio results are under:

```text
Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_minimal
```

For the current recommended audio settings, use `AUDIO_PROMPT_STYLE=strict`. This sends `/no_think` as a system message and asks for only the transcript in the user message.

If Hugging Face warns about unauthenticated downloads, set a free `HF_TOKEN` in `.env` or your shell. Public dataset downloads do not require paid Hugging Face usage, but NVIDIA API calls may consume NVIDIA credits.

## Compare all reproduced results

Once the benchmark stdout files exist in `Instructor-Assistant/olmocr_bench_workspace/results`, run:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl compare
```

That prints one line per candidate with:

- average score
- confidence interval half-width
- failed test count
- empty markdown file count

## Empty-file cleanup and resume

Count empty candidate outputs:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl clean-empty --candidate svr_ocr_full
```

Delete empty candidate outputs before a resume run:

```bash
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl clean-empty --candidate svr_ocr_full --delete
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
Instructor-Assistant/olmocr_bench_workspace/scripts/setup_workspace.sh
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl validate
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl download-bench-data

Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_pdf_eval.sh
Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_audio_eval.sh

Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl convert-qwen-structured --parallel 1
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl postprocess-qwen --force
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl convert-olmocr2 --parallel 1
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl convert-svr --parallel 4 --target-longest-image-dim 1024

Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate qwen_structured_post
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate olmocr2
Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl benchmark --candidate svr_ocr_full

Instructor-Assistant/olmocr_bench_workspace/scripts/benchctl compare
```
