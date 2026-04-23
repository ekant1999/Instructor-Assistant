# SVR-OCR Source Package

This directory contains the Python scaffold for the `SVR-OCR` implementation.

## Package root

- `svr_ocr`

## Current scope

The scaffold currently defines the first full-build implementation slice:

- layout graph construction
- typed refinement planning
- endpoint-backed block transcription
- verification
- repair
- page/document assembly
- top-level pipeline orchestration
- `olmOCR-Bench` candidate generation adapter

The code is intentionally interface-first. It is designed to let the project swap in stronger layout detectors, renderers, image crops, and benchmark runners without rewriting the core contracts.

## Import path

Use:

```bash
PYTHONPATH=SVR-OCR/src python -c "import svr_ocr; print(svr_ocr.__all__)"
```

## Real endpoint path

For OpenAI-compatible vision backends such as DashScope/Qwen, use:

```python
from svr_ocr import build_openai_compatible_pipeline, EndpointConfig

pipeline = build_openai_compatible_pipeline(
    endpoint=EndpointConfig.from_env(
        base_url_env="QWEN_SERVER",
        model_env="QWEN_MODEL",
        api_key_env="QWEN_API_KEY",
    )
)
```

This expects an OpenAI-compatible `chat/completions` endpoint under the configured base URL.

## Live smoke test

```bash
PYTHONPATH=SVR-OCR/src python SVR-OCR/scripts/smoke_openai_compatible.py \
  --image "/path/to/page.png" \
  --show-provenance
```

Or render page 1 from a PDF before sending it to the endpoint:

```bash
PYTHONPATH=SVR-OCR/src python SVR-OCR/scripts/smoke_openai_compatible.py \
  --pdf "/path/to/sample.pdf" \
  --page 1 \
  --show-provenance
```

## `olmOCR-Bench` candidate generation

```bash
PYTHONPATH=SVR-OCR/src python -m svr_ocr.eval.bench_runner \
  --pdf-dir ~/ocr-paper-work/olmOCR-bench/bench_data/pdfs \
  --output-dir ~/ocr-paper-work/olmOCR-bench/bench_data/svr_ocr_full \
  --base-url-env QWEN_SERVER \
  --model-env QWEN_MODEL \
  --api-key-env QWEN_API_KEY \
  --parallel 4 \
  --max-tokens 2000 \
  --target-longest-image-dim 1024
```

This writes benchmark-compatible markdown files to the requested candidate folder using the same output naming pattern as `olmocr.bench.convert`.

Use the margin-aware seed mode for the header/footer omission ablation:

```bash
PYTHONPATH=SVR-OCR/src python -m svr_ocr.eval.bench_runner \
  --pdf-dir ~/ocr-paper-work/olmOCR-bench/bench_data/pdfs \
  --output-dir ~/ocr-paper-work/olmOCR-bench/bench_data/svr_ocr_full_margin_aware \
  --base-url-env QWEN_SERVER \
  --model-env QWEN_MODEL \
  --api-key-env QWEN_API_KEY \
  --parallel 4 \
  --max-tokens 2000 \
  --target-longest-image-dim 1024 \
  --page-seed-mode margin_aware
```
