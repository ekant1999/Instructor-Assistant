#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$WORKSPACE_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

export PYTHONPATH="$WORKSPACE_DIR/../../ocr-paper-work/olmocr${PYTHONPATH:+:$PYTHONPATH}"
export NVIDIA_CANDIDATE="${NVIDIA_CANDIDATE:-nemotron_omni_nvidia_ocr_structured_quality5}"
export NVIDIA_PROMPT_TEMPLATE="${NVIDIA_PROMPT_TEMPLATE:-nvidia_ocr_structured}"

"$WORKSPACE_DIR/.venv/bin/python" "$WORKSPACE_DIR/scripts/run_nvidia_quality5.py"

echo
echo "Structured quality-5 outputs:"
echo "  $WORKSPACE_DIR/data/olmOCR-bench/bench_data_nvidia_quality5_v2/$NVIDIA_CANDIDATE"
echo "  $WORKSPACE_DIR/data/olmOCR-bench/bench_data_nvidia_quality5_v2/manifest.json"
