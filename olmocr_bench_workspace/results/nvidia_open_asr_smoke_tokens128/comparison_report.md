# NVIDIA Nemotron Omni ASR Smoke Comparison

## Setup

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Datasets sampled:
  - `librispeech:test.clean`
  - `librispeech:test.other`
  - `common_voice:test`
  - `ami:test`
  - `earnings22:test`
- Sample count: 50 short clips
- Max clip duration: 3 seconds
- Delivery mode: inline audio

## Result

Reducing the output cap to `max_tokens=128` substantially improved stability.

```text
Run                         Success   Avg WER   Prompt/output issues
max_tokens=512 smoke        48/50     2.683     prompt leaks, loops, 2 timeouts
max_tokens=128 smoke        50/50     0.445     2 prompt leaks, no timeouts
```

Per-dataset WER for the improved `max_tokens=128` run:

```text
librispeech   0.109 over 20 clips
common_voice  0.100 over 10 clips
ami           0.557 over 10 clips
earnings22    1.348 over 10 clips
```

## Findings

The model performs well on short clean read speech. LibriSpeech and Common Voice were much stronger after lowering `max_tokens`.

Meeting and business-call speech remain harder. AMI had moderate WER, and Earnings-22 had one severe outlier that inflated the dataset average.

The main failure mode is still instruction leakage rather than ordinary ASR substitution. In the `max_tokens=128` run, 48/50 outputs were normal, while 2 leaked prompt/system text or reasoning-style content.

The large-audio asset-upload path was not usable in this setup: NVIDIA returned `501 Not Implemented` when using the NVCF asset route through the OpenAI-compatible chat endpoint. For now, this runner keeps clips short and sends audio inline.

## Recommendation

Use the `max_tokens=128` settings for the next run. The next reasonable scale is 100-250 short clips, still with `--max-duration 3`, before attempting longer audio.

Suggested next command:

```bash
./Instructor-Assistant/olmocr_bench_workspace/.venv/bin/python \
  Instructor-Assistant/olmocr_bench_workspace/scripts/run_nvidia_open_asr.py \
  --datasets librispeech:test.clean librispeech:test.other common_voice:test ami:test earnings22:test \
  --samples-per-dataset 25 \
  --max-duration 3 \
  --max-tokens 128 \
  --output-dir Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128
```

Then summarize:

```bash
./Instructor-Assistant/olmocr_bench_workspace/.venv/bin/python \
  Instructor-Assistant/olmocr_bench_workspace/scripts/summarize_nvidia_asr.py \
  Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128/predictions.jsonl
```
