#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$WORKSPACE_DIR/../.." && pwd)"
ENV_FILE="$WORKSPACE_DIR/.env"
BENCH_SRC="$WORKSPACE_DIR/data/olmOCR-bench/bench_data"
SMOKE_DIR="$WORKSPACE_DIR/data/olmOCR-bench/bench_data_nvidia_smoke"
PYTHON_BIN="$WORKSPACE_DIR/.venv/bin/python"
PATCHED_OLMOCR="$REPO_ROOT/ocr-paper-work/olmocr"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing workspace Python venv: $PYTHON_BIN"
  echo "Run scripts/setup_workspace.sh first."
  exit 1
fi

if [[ ! -d "$PATCHED_OLMOCR/olmocr/bench/runners" ]]; then
  echo "Missing patched olmocr checkout: $PATCHED_OLMOCR"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

required_env=(NVIDIA_SERVER NVIDIA_MODEL NVIDIA_API_KEY)
for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing environment variable after sourcing .env: $name"
    exit 1
  fi
done

if [[ ! -d "$BENCH_SRC/pdfs" ]]; then
  echo "Missing benchmark PDFs: $BENCH_SRC/pdfs"
  exit 1
fi

rm -rf "$SMOKE_DIR"
mkdir -p "$SMOKE_DIR/pdfs"
pdf="$BENCH_SRC/pdfs/tables/0091c5b23fe54b3a7cbe5b0b8c26057b7d70_pg3_pg1.pdf"
if [[ ! -f "$pdf" ]]; then
  pdf="$(find "$BENCH_SRC/pdfs/tables" -type f -name '*.pdf' | sort | awk 'NR == 1')"
fi
rel="${pdf#"$BENCH_SRC/pdfs/"}"
mkdir -p "$SMOKE_DIR/pdfs/$(dirname "$rel")"
cp "$pdf" "$SMOKE_DIR/pdfs/$rel"
echo "smoke_pdf_count=$(find "$SMOKE_DIR/pdfs" -type f -name '*.pdf' | wc -l | tr -d ' ')"

export PYTHONPATH="$PATCHED_OLMOCR${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/3] Preflight"
"$PYTHON_BIN" - <<'PY'
import inspect
import os

import httpx
import olmocr.bench.runners.run_server as rs

print("runner_file=", rs.__file__)
print("has_endpoint_env=", "endpoint_env" in str(inspect.signature(rs.run_server)))
print("server=", os.environ["NVIDIA_SERVER"])
print("model=", os.environ["NVIDIA_MODEL"])
print("api_key_set=", bool(os.environ.get("NVIDIA_API_KEY")))

url = os.environ["NVIDIA_SERVER"].rstrip("/") + "/models"
response = httpx.get(url, headers={"Authorization": "Bearer " + os.environ["NVIDIA_API_KEY"]}, timeout=30)
print("models_status=", response.status_code)
response.raise_for_status()
PY

echo "[2/3] Running NVIDIA smoke conversion"
"$PYTHON_BIN" -m olmocr.bench.convert \
  --dir "$SMOKE_DIR" \
  --repeats 1 \
  --parallel 1 \
  --force \
  --failfast \
  "server:name=nemotron_omni:model=${NVIDIA_MODEL}:endpoint_env=NVIDIA_SERVER:api_key_env=NVIDIA_API_KEY:prompt_template=fullv3simple:response_template=plain:max_tokens=1024:target_longest_image_dim=512:enable_thinking=false:allow_non_stop=true"

echo "[3/3] Output check"
find "$SMOKE_DIR/nemotron_omni" -type f -name '*.md' | wc -l
find "$SMOKE_DIR/nemotron_omni" -type f -name '*.md' -size 0 -print
first_md="$(find "$SMOKE_DIR/nemotron_omni" -type f -name '*.md' | head -1)"
if [[ -n "$first_md" ]]; then
  echo
  echo "First output: $first_md"
  head -c 1200 "$first_md"
  echo
fi
