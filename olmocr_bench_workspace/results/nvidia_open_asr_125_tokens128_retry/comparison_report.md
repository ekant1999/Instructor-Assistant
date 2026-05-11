# NVIDIA Nemotron Omni ASR 125-Sample Retry Report

## Setup

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Datasets:
  - `librispeech:test.clean`
  - `librispeech:test.other`
  - `common_voice:test`
  - `ami:test`
  - `earnings22:test`
- Samples requested: 125
- Max clip duration: 3 seconds
- Max output tokens: 128
- Audio delivery: inline
- Retry/backoff enabled for rate limits

## Result

The retry/backoff run improved API completion rate but did not materially solve transcription instability.

```text
Run                         Success   Avg WER
50-sample tokens128          50/50    0.445
125-sample tokens128        112/125   1.094
125-sample tokens128 retry  124/125   1.044
```

Per-dataset WER for the retry run:

```text
ami           0.345 over 25 clips
common_voice  1.637 over 25 clips
earnings22    1.910 over 25 clips
librispeech   0.655 over 49 clips
```

## Reliability

The retry run reduced API failures from 13 to 1:

```text
previous 125-sample run: 13 HTTP 429 errors
retry 125-sample run:     1 ReadTimeout error
```

So the `--request-sleep`, `--retries`, and `--retry-sleep` options are effective for API rate-limit reliability.

## Quality Issues

The remaining problem is model behavior, not dataset loading or API availability.

Output flags:

```text
normal:      112
repeat_loop:   7
prompt_leak:   5
zero_loop:     2
```

Worst failures include:

- repeating phrases such as `simplified text:` or `the first line is`
- leaking the system prompt: `You are a speech-to-text transcription engine`
- reasoning about images or text instead of transcribing audio
- inserting unrelated content such as dates, zeros, or hallucinated context

## Interpretation

The model can transcribe short clips correctly, especially clean read speech and some meeting clips. However, at 125 samples the average WER remains high because a small number of severe hallucination/loop failures dominate the score.

This mirrors the OCR benchmark behavior: the model has multimodal capability, but output control is unreliable for benchmark-grade extraction.

## Recommendation

Use this as a preliminary audio result, not a final ASR benchmark result.

For a professor-facing summary:

> On short Open ASR Leaderboard clips, NVIDIA Nemotron Omni processed audio successfully with retry/backoff, but transcription quality was unstable. The best 50-sample run achieved WER 0.445 with no API errors, while the larger 125-sample retry run achieved WER 1.044 with 124/125 completions. Failures were dominated by prompt leakage, repeated text loops, and hallucinated reasoning rather than ordinary ASR substitutions.

Next technical step: test a different audio request format or a different NVIDIA audio-capable model before scaling further.
