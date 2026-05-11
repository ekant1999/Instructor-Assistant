# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_25_strict`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Prompt style: `strict`
- Successful samples: 25 / 25

- Average normalized WER: `0.458`

## Per Dataset

- `ami`: WER `0.247` over 5 samples
- `common_voice`: WER `0.000` over 5 samples
- `earnings22`: WER `1.853` over 5 samples
- `librispeech`: WER `0.094` over 10 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_25_strict/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_25_strict/audio`
