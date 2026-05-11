# NVIDIA Nemotron Omni ASR Strict Prompt Report

## Setup

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Samples requested: 125
- Prompt style: `strict`
- System prompt: `/no_think`
- User prompt: `Transcribe the spoken words in this audio. Return only the transcript.`
- Max clip duration: 3 seconds
- Max output tokens: 128
- Audio delivery: inline

## Result

```text
Run                         Success   Avg WER   Notes
default prompt              112/125   1.094     13 rate-limit errors, prompt leaks
default prompt + retry      124/125   1.044     5 prompt leaks, 7 repeat loops
minimal prompt              125/125   1.142     0 prompt leaks, 9 repeat loops
strict prompt               124/125   0.783     0 prompt leaks, 4 repeat loops, 1 timeout
```

Per-dataset WER for the strict run:

```text
librispeech    1.345 over 49 clips
common_voice   0.539 over 25 clips
ami            0.555 over 25 clips
earnings22     0.153 over 25 clips
```

Distribution:

```text
perfect WER       72 / 124
WER <= 0.2        86 / 124
WER <= 0.5       101 / 124
WER > 1           13 / 124
median WER       0.0
```

The average WER excluding samples with WER >= 5 is approximately `0.288` over 118 successful samples.

## Findings

The strict prompt substantially improved the audio evaluation. It removed explicit prompt leaks and reduced the overall WER compared with the earlier 125-sample runs.

However, severe failures remain. The worst examples still include:

- hallucinated image/text reasoning
- extra explanation after an otherwise correct transcript
- repeated text loops
- one read timeout

The main remaining weakness is not ordinary ASR word mistakes. It is occasional mode collapse into general multimodal reasoning instead of strict transcription. This is why the median WER is perfect while the average WER is still high: many samples are correct, but a small number of severe outliers dominate the score.

## Interpretation

The strict prompt supports the conclusion that the earlier poor results were partly caused by prompt and inference settings. The model can transcribe many short audio clips correctly.

At the same time, this NVIDIA Omni API route remains unreliable for benchmark-grade ASR because it occasionally produces non-transcription reasoning output. For a professor-facing report, the most accurate framing is:

> A stricter NVIDIA-compatible audio prompt significantly improved transcription behavior, but the model still had intermittent hallucination and repetition failures. The endpoint is usable for demonstrating audio input capability, but it is not stable enough to treat as a dedicated ASR benchmark system without additional output validation or retries.
