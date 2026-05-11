# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke_tokens128`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Successful samples: 50 / 50

- Average normalized WER: `0.445`

## Per Dataset

- `ami`: WER `0.557` over 10 samples
- `common_voice`: WER `0.100` over 10 samples
- `earnings22`: WER `1.348` over 10 samples
- `librispeech`: WER `0.109` over 20 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke_tokens128/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke_tokens128/audio`
