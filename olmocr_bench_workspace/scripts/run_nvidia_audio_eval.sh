#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  scripts/run_nvidia_audio_eval.sh

Runs the NVIDIA Nemotron Omni audio transcription evaluation on short
Open ASR Leaderboard clips:
  1. source NVIDIA credentials from ../.env
  2. download/select short audio clips from Hugging Face
  3. call the NVIDIA chat/completions API with inline audio
  4. compute WER
  5. write report.md, predictions.jsonl, and analysis.md

Default run:
  50 samples from each of 5 dataset specs = 250 requested samples

Environment overrides:
  AUDIO_OUTPUT_DIR=results/nvidia_open_asr_250_tokens128_minimal
  AUDIO_SAMPLES_PER_DATASET=50
  AUDIO_MAX_DURATION=3
  AUDIO_MAX_TOKENS=128
  AUDIO_REQUEST_SLEEP=3
  AUDIO_RETRIES=6
  AUDIO_RETRY_SLEEP=5
  AUDIO_PROMPT_STYLE=strict    # default|minimal|strict|none
  AUDIO_DATASETS="librispeech:test.clean librispeech:test.other common_voice:test ami:test earnings22:test"

Optional Hugging Face:
  HF_TOKEN=...

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
PYTHON_BIN="$WORKSPACE_DIR/.venv/bin/python"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing workspace Python venv: $PYTHON_BIN"
  echo "Run scripts/setup_workspace.sh first."
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

AUDIO_OUTPUT_DIR="${AUDIO_OUTPUT_DIR:-$WORKSPACE_DIR/results/nvidia_open_asr_250_tokens128_minimal}"
AUDIO_SAMPLES_PER_DATASET="${AUDIO_SAMPLES_PER_DATASET:-50}"
AUDIO_MAX_DURATION="${AUDIO_MAX_DURATION:-3}"
AUDIO_MAX_TOKENS="${AUDIO_MAX_TOKENS:-128}"
AUDIO_REQUEST_SLEEP="${AUDIO_REQUEST_SLEEP:-3}"
AUDIO_RETRIES="${AUDIO_RETRIES:-6}"
AUDIO_RETRY_SLEEP="${AUDIO_RETRY_SLEEP:-5}"
AUDIO_PROMPT_STYLE="${AUDIO_PROMPT_STYLE:-strict}"
AUDIO_DATASETS="${AUDIO_DATASETS:-librispeech:test.clean librispeech:test.other common_voice:test ami:test earnings22:test}"

read -r -a DATASET_ARGS <<< "$AUDIO_DATASETS"

mkdir -p "$AUDIO_OUTPUT_DIR"

echo "============================================================"
echo "NVIDIA audio ASR eval"
echo "workspace=$WORKSPACE_DIR"
echo "output_dir=$AUDIO_OUTPUT_DIR"
echo "model=$NVIDIA_MODEL"
echo "datasets=${DATASET_ARGS[*]}"
echo "samples_per_dataset=$AUDIO_SAMPLES_PER_DATASET"
echo "max_duration=$AUDIO_MAX_DURATION"
echo "max_tokens=$AUDIO_MAX_TOKENS"
echo "prompt_style=$AUDIO_PROMPT_STYLE"
echo "============================================================"

echo "[1/2] Running audio transcription eval"
"$PYTHON_BIN" "$WORKSPACE_DIR/scripts/run_nvidia_open_asr.py" \
  --datasets "${DATASET_ARGS[@]}" \
  --samples-per-dataset "$AUDIO_SAMPLES_PER_DATASET" \
  --max-duration "$AUDIO_MAX_DURATION" \
  --max-tokens "$AUDIO_MAX_TOKENS" \
  --request-sleep "$AUDIO_REQUEST_SLEEP" \
  --retries "$AUDIO_RETRIES" \
  --retry-sleep "$AUDIO_RETRY_SLEEP" \
  --prompt-style "$AUDIO_PROMPT_STYLE" \
  --output-dir "$AUDIO_OUTPUT_DIR"

echo "[2/2] Summarizing audio outputs"
"$PYTHON_BIN" "$WORKSPACE_DIR/scripts/summarize_nvidia_asr.py" \
  "$AUDIO_OUTPUT_DIR/predictions.jsonl"

echo
echo "Audio eval outputs:"
echo "  predictions: $AUDIO_OUTPUT_DIR/predictions.jsonl"
echo "  report     : $AUDIO_OUTPUT_DIR/report.md"
echo "  analysis   : $AUDIO_OUTPUT_DIR/analysis.md"
echo "  audio cache: $AUDIO_OUTPUT_DIR/audio"
