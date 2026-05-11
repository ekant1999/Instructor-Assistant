# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Successful samples: 48 / 50

- Average normalized WER: `2.683`

## Per Dataset

- `ami`: WER `0.734` over 10 samples
- `common_voice`: WER `4.186` over 10 samples
- `earnings22`: WER `0.599` over 10 samples
- `librispeech`: WER `4.090` over 18 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke/audio`
