#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  scripts/run_nvidia_full_convert.sh

Environment overrides:
  NVIDIA_CANDIDATE=nemotron_omni_nvidia_ocr
  NVIDIA_PARALLEL=1
  NVIDIA_PROMPT_TEMPLATE=nvidia_ocr

The script sources ../.env, verifies the patched NVIDIA-capable runner is
imported, checks the NVIDIA /models endpoint, and runs olmOCR-Bench conversion.
EOF
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$WORKSPACE_DIR/../.." && pwd)"
ENV_FILE="$WORKSPACE_DIR/.env"
BENCH_DIR="$WORKSPACE_DIR/data/olmOCR-bench/bench_data"
PYTHON_BIN="$WORKSPACE_DIR/.venv/bin/python"
PATCHED_OLMOCR="$REPO_ROOT/ocr-paper-work/olmocr"
CANDIDATE="${NVIDIA_CANDIDATE:-nemotron_omni_nvidia_ocr}"
PARALLEL="${NVIDIA_PARALLEL:-1}"
PROMPT_TEMPLATE="${NVIDIA_PROMPT_TEMPLATE:-nvidia_ocr}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
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

if [[ ! -d "$BENCH_DIR/pdfs" ]]; then
  echo "Missing benchmark PDFs: $BENCH_DIR/pdfs"
  exit 1
fi

export PYTHONPATH="$PATCHED_OLMOCR${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/2] Preflight"
"$PYTHON_BIN" - <<'PY'
import inspect
import os

import httpx
import olmocr.bench.runners.run_server as rs

runner_file = rs.__file__
signature = str(inspect.signature(rs.run_server))
print("runner_file=", runner_file)
print("server=", os.environ["NVIDIA_SERVER"])
print("model=", os.environ["NVIDIA_MODEL"])
print("api_key_set=", bool(os.environ.get("NVIDIA_API_KEY")))

if "ocr-paper-work/olmocr" not in runner_file:
    raise SystemExit("Refusing to run: patched ocr-paper-work/olmocr runner is not being imported")
for name in ["endpoint_env", "api_key_env", "prompt_template", "image_format", "enable_thinking"]:
    if name not in signature:
        raise SystemExit(f"Refusing to run: runner does not support {name}")

url = os.environ["NVIDIA_SERVER"].rstrip("/") + "/models"
response = httpx.get(url, headers={"Authorization": "Bearer " + os.environ["NVIDIA_API_KEY"]}, timeout=30)
print("models_status=", response.status_code)
response.raise_for_status()
PY

echo "[2/2] Full NVIDIA conversion"
echo "candidate=$CANDIDATE"
echo "parallel=$PARALLEL"
echo "prompt_template=$PROMPT_TEMPLATE"

"$PYTHON_BIN" -m olmocr.bench.convert \
  --dir "$BENCH_DIR" \
  --repeats 1 \
  --parallel "$PARALLEL" \
  "server:name=${CANDIDATE}:model=${NVIDIA_MODEL}:endpoint_env=NVIDIA_SERVER:api_key_env=NVIDIA_API_KEY:prompt_template=${PROMPT_TEMPLATE}:response_template=plain:target_longest_image_dim=1024:image_format=jpeg:jpeg_quality=85:max_tokens=4096:enable_thinking=false:allow_non_stop=true"
