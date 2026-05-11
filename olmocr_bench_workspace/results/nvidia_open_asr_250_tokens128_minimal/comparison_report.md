# NVIDIA Nemotron Omni ASR Expanded Minimal Prompt Report

## Setup

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Dataset source: `hf-audio/open-asr-leaderboard`
- Output directory: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_minimal`
- Prompt style: `minimal`
- Prompt text: `/no_think\nTranscribe:`
- Max clip duration: 3 seconds
- Max output tokens: 128
- Audio delivery: inline

## Important Note

This run contains 500 rows, not 250. The sample distribution was:

```text
librispeech    200
common_voice   100
ami            100
earnings22     100
```

The likely reason is that the run used two LibriSpeech configs plus the other datasets with a higher `--samples-per-dataset` value than the intended 50.

## Result

```text
Run                         Success   Avg WER   Notes
125 minimal prompt           125/125   1.142     0 prompt leaks, 9 repeat loops
expanded minimal prompt      496/500   1.382     1 prompt leak, 35 repeat loops
```

Per-dataset WER:

```text
librispeech    1.177 over 200 clips
common_voice   1.402 over 100 clips
ami            1.701 over 97 clips
earnings22     1.462 over 99 clips
```

Output flags:

```text
normal         458
repeat_loop     35
zero_loop        5
prompt_leak      1
empty            1
```

API errors:

```text
ReadTimeout      4
```

## Findings

Scaling up made the quality problem clearer. The model still produced repeated-output loops, hallucinated reasoning, and image/text-task language during an audio transcription benchmark. The minimal prompt mostly prevents direct prompt leakage, but it does not prevent the model from reasoning aloud or drifting away from ASR.

The expanded run also has worse WER than the 125-sample minimal run, increasing from `1.142` to `1.382`. AMI was the weakest subset, followed by Earnings22 and Common Voice. LibriSpeech was best, but still far above expected ASR benchmark quality.

## Interpretation

The main issue is not just our prompt. The prompt can reduce explicit leakage, but the model/API route remains unstable for transcription. For a professor-facing report, this expanded run supports the conclusion that Nemotron Omni can accept and process short audio inputs, but is not reliable enough for benchmark-grade ASR evaluation in this setup.
