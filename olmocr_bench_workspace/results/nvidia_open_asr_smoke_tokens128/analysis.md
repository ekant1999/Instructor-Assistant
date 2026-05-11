# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke_tokens128/predictions.jsonl`
- Rows: 50
- Successful: 50
- Errors: 0

- Raw average WER: `0.445`
- Cleaned average WER: `0.445`

## Per Dataset

- `ami`: raw WER `0.557`, cleaned WER `0.557`, n=10
- `common_voice`: raw WER `0.100`, cleaned WER `0.100`, n=10
- `earnings22`: raw WER `1.348`, cleaned WER `1.348`, n=10
- `librispeech`: raw WER `0.109`, cleaned WER `0.109`, n=20

## Output Flags

- `normal`: 48
- `prompt_leak`: 2

## Worst Examples

### earnings22 / 4483338/284.wav

- Raw WER: `9.500`
- Cleaned WER: `9.500`
- Flags: `normal`

Reference: And I think we have sort of been guiding that.

Prediction: And the text is "And I need to check if there and what the user is asking for. Let me analyze the conversation:

The user's last message was: "And I think we've sort of been guiding that what"

This appears to be a continuation of a previous conversation, but I don't have the full context. The user seems to be asking about what they've been "guiding" - possibly referring to some guidance or guidance they've been providing.

However, I don't have enough context to understand what they're specifically asking about. They might be asking:
1. What they've sort of sort of been guiding (

### ami / AMI_EN2002c_H03_MEE073_0170922_0171222

- Raw WER: `1.833`
- Cleaned WER: `1.833`
- Flags: `normal`

Reference: Let's not make it more complicated.

Prediction: Let's see. So the transcription is "Let's. So the transcription is "Let's not make it more complicated."

### ami / AMI_EN2002d_H01_FEO072_0025012_0025312

- Raw WER: `1.500`
- Cleaned WER: `1.500`
- Flags: `normal`

Reference: Yeah, yeah.

Prediction: Yeah, yeah. 0. 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
Yeah, yeah.

### earnings22 / 4479741/336.wav

- Raw WER: `1.200`
- Cleaned WER: `1.200`
- Flags: `prompt_leak`

Reference: So maybe help me understand how strong that number is.

Prediction: You are a speech-to-text transcription engine. Return only the transcript.
