# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_minimal`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Prompt style: `minimal`
- Successful samples: 125 / 125

- Average normalized WER: `1.142`

## Per Dataset

- `ami`: WER `1.421` over 25 samples
- `common_voice`: WER `1.162` over 25 samples
- `earnings22`: WER `1.418` over 25 samples
- `librispeech`: WER `0.854` over 50 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_minimal/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_minimal/audio`
