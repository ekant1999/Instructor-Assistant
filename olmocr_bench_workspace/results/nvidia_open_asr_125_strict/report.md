# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_strict`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Prompt style: `strict`
- Successful samples: 124 / 125

- Average normalized WER: `0.783`

## Per Dataset

- `ami`: WER `0.555` over 25 samples
- `common_voice`: WER `0.539` over 25 samples
- `earnings22`: WER `0.153` over 25 samples
- `librispeech`: WER `1.345` over 49 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_strict/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_strict/audio`
