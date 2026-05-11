# NVIDIA Nemotron Omni ASR Smoke Report

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128`
- Requested datasets: `librispeech:test.clean, librispeech:test.other, common_voice:test, ami:test, earnings22:test`
- Successful samples: 112 / 125

- Average normalized WER: `1.094`

## Per Dataset

- `ami`: WER `1.370` over 22 samples
- `common_voice`: WER `1.760` over 25 samples
- `earnings22`: WER `0.538` over 24 samples
- `librispeech`: WER `0.865` over 41 samples

## Files

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128/predictions.jsonl`
- Audio cache: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128/audio`
