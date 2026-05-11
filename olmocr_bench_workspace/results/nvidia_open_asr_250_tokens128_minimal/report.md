# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_minimal`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Prompt style: `minimal`
- Successful samples: 496 / 500

- Average normalized WER: `1.382`

## Per Dataset

- `ami`: WER `1.701` over 97 samples
- `common_voice`: WER `1.402` over 100 samples
- `earnings22`: WER `1.462` over 99 samples
- `librispeech`: WER `1.177` over 200 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_minimal/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_minimal/audio`
