# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_25_strict/predictions.jsonl`
- Rows: 25
- Successful: 25
- Errors: 0

- Raw average WER: `0.458`
- Cleaned average WER: `0.458`

## Per Dataset

- `ami`: raw WER `0.247`, cleaned WER `0.247`, n=5
- `common_voice`: raw WER `0.000`, cleaned WER `0.000`, n=5
- `earnings22`: raw WER `1.853`, cleaned WER `1.853`, n=5
- `librispeech`: raw WER `0.094`, cleaned WER `0.094`, n=10

## Output Flags

- `normal`: 23
- `repeat_loop`: 2

## Worst Examples

### earnings22 / 4479741/308.wav

- Raw WER: `8.273`
- Cleaned WER: `8.273`
- Flags: `repeat_loop`

Reference: Thank you um, thank you Alex for your um, your questions.

Prediction: Thank you for your interest in the project. The project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is thank you for your interest in the project. The project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project is a success. The  project
