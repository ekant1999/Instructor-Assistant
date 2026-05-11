# NVIDIA Nemotron Omni ASR Minimal Prompt Report

## Setup

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Samples requested: 125
- Max clip duration: 3 seconds
- Max output tokens: 128
- Prompt style: `minimal`
- Prompt text: `/no_think\nTranscribe:`
- Audio delivery: inline

## Result

The minimal prompt eliminated explicit prompt leakage and completed all samples, but it did not improve WER.

```text
Run                         Success   Avg WER   Notes
default prompt + retry      124/125   1.044     5 prompt leaks, 7 repeat loops
minimal prompt              125/125   1.142     0 prompt leaks, 9 repeat loops
```

Per-dataset WER for minimal prompt:

```text
librispeech   0.854 over 50 clips
common_voice  1.162 over 25 clips
ami           1.421 over 25 clips
earnings22    1.418 over 25 clips
```

## Findings

The minimal prompt confirms that some leaked text came from our previous instruction prompt. Removing that instruction text eliminated explicit `You are a speech-to-text transcription engine` leakage.

However, severe failures remain:

- repeated text loops
- date/number garbage
- hallucinated reasoning
- references to images despite audio input
- over-explanation instead of transcription

Output flags:

```text
normal:      116
repeat_loop:   9
zero_loop:     2
prompt_leak:   0
```

## Interpretation

Prompt design matters, but the dominant issue is still model/API behavior. The model sometimes treats the task as general multimodal reasoning rather than strict ASR, even with a minimal prompt and `enable_thinking=false`.

The best result remains the smaller 50-sample `max_tokens=128` run:

```text
50-sample tokens128: 0.445 WER, 50/50 success
```

The 125-sample runs expose instability that the smaller smoke test did not fully reveal.

## Recommendation

Do not expand to a larger ASR benchmark with this model/API route yet.

For reporting, use the minimal prompt run to support this conclusion:

> We reduced prompt leakage by switching to a minimal prompt, but the model continued to produce repeated text loops and hallucinated reasoning. This suggests that the main limitation is not only prompt wording; the model/API route is not reliable enough for benchmark-grade ASR extraction.
