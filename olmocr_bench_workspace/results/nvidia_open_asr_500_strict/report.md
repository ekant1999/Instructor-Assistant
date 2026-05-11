# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_500_strict`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Prompt style: `strict`
- Successful samples: 491 / 500

- Average normalized WER: `0.990`

## Per Dataset

- `ami`: WER `0.787` over 99 samples
- `common_voice`: WER `1.180` over 98 samples
- `earnings22`: WER `1.070` over 98 samples
- `librispeech`: WER `0.957` over 196 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_500_strict/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_500_strict/audio`
