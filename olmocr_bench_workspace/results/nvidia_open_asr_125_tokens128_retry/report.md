# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_retry`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Successful samples: 124 / 125

- Average normalized WER: `1.044`

## Per Dataset

- `ami`: WER `0.345` over 25 samples
- `common_voice`: WER `1.637` over 25 samples
- `earnings22`: WER `1.910` over 25 samples
- `librispeech`: WER `0.655` over 49 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_retry/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_retry/audio`
