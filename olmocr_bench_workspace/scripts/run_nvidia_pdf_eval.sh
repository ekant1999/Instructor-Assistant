#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  scripts/run_nvidia_pdf_eval.sh

Runs the NVIDIA Nemotron Omni PDF/OCR evaluation on olmOCR-Bench:
  1. preflight NVIDIA API and patched olmOCR runner
  2. convert benchmark PDFs to Markdown with NVIDIA Omni
  3. run olmOCR-Bench scoring
  4. print and save a compact summary

Default output candidate:
  nemotron_omni_nvidia_ocr

Environment overrides:
  NVIDIA_CANDIDATE=nemotron_omni_nvidia_ocr
  NVIDIA_PARALLEL=1
  NVIDIA_PROMPT_TEMPLATE=nvidia_ocr
  NVIDIA_BOOTSTRAP_SAMPLES=200
  NVIDIA_MAX_REPORTS=20
  NVIDIA_SKIP_CONVERT=1       # score existing candidate outputs only

Required in ../.env:
  NVIDIA_SERVER
  NVIDIA_MODEL
  NVIDIA_API_KEY
EOF
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$WORKSPACE_DIR/.env"
CANDIDATE="${NVIDIA_CANDIDATE:-nemotron_omni_nvidia_ocr}"
BOOTSTRAP_SAMPLES="${NVIDIA_BOOTSTRAP_SAMPLES:-200}"
MAX_REPORTS="${NVIDIA_MAX_REPORTS:-20}"
SUMMARY_PATH="$WORKSPACE_DIR/results/${CANDIDATE}_demo_summary.txt"

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

mkdir -p "$WORKSPACE_DIR/results"

echo "============================================================"
echo "NVIDIA PDF/OCR eval"
echo "workspace=$WORKSPACE_DIR"
echo "candidate=$CANDIDATE"
echo "model=$NVIDIA_MODEL"
echo "parallel=${NVIDIA_PARALLEL:-1}"
echo "prompt_template=${NVIDIA_PROMPT_TEMPLATE:-nvidia_ocr}"
echo "bootstrap_samples=$BOOTSTRAP_SAMPLES"
echo "============================================================"

if [[ "${NVIDIA_SKIP_CONVERT:-0}" == "1" ]]; then
  echo "[1/3] Skipping conversion; using existing candidate outputs"
else
  echo "[1/3] Running conversion"
  NVIDIA_CANDIDATE="$CANDIDATE" "$SCRIPT_DIR/run_nvidia_full_convert.sh"
fi

echo "[2/3] Running olmOCR-Bench scoring"
"$SCRIPT_DIR/benchctl" benchmark \
  --candidate "$CANDIDATE" \
  --bootstrap-samples "$BOOTSTRAP_SAMPLES" \
  --max-reports "$MAX_REPORTS"

echo "[3/3] Summary"
"$SCRIPT_DIR/benchctl" summarize --candidate "$CANDIDATE" | tee "$SUMMARY_PATH"

echo
echo "PDF eval outputs:"
echo "  candidate markdown: $WORKSPACE_DIR/data/olmOCR-bench/bench_data/$CANDIDATE"
echo "  HTML report       : $WORKSPACE_DIR/results/${CANDIDATE}_report.html"
echo "  failed checks     : $WORKSPACE_DIR/results/${CANDIDATE}_failed.jsonl"
echo "  stdout            : $WORKSPACE_DIR/results/${CANDIDATE}_stdout.txt"
echo "  demo summary      : $SUMMARY_PATH"
