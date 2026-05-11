# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_smoke/predictions.jsonl`
- Rows: 50
- Successful: 48
- Errors: 2

- Raw average WER: `2.683`
- Cleaned average WER: `2.169`

## Per Dataset

- `ami`: raw WER `0.734`, cleaned WER `0.734`, n=10
- `common_voice`: raw WER `4.186`, cleaned WER `4.186`, n=10
- `earnings22`: raw WER `0.599`, cleaned WER `0.599`, n=10
- `librispeech`: raw WER `4.090`, cleaned WER `2.720`, n=18

## Output Flags

- `normal`: 43
- `prompt_leak`: 3
- `repeat_loop`: 2
- `zero_loop`: 1
- `refusal_loop`: 1

## API Errors

- `librispeech` `8455-210777-0026`: ReadTimeout - The read operation timed out
- `librispeech` `3729-6852-0025`: ReadTimeout - The read operation timed out

## Worst Examples

### librispeech / 8188-269288-0052

- Raw WER: `40.800`
- Cleaned WER: `40.800`
- Flags: `prompt_leak`

Reference: annie's manner was very mysterious

Prediction: Annie's manner was very mysterious. (Wait, the prompt says "Transcribe this audio exactly." but the image provided is a picture of text? No, the image is Annie's manner was very mysterious. (Wait, the prompt says "Transcribe this audio exactly." but the image provided is a picture of text? No, the image provided is a picture of text? No, the image provided is a text file. The response should be the content of the file without any additional formatting or commentary.

However, the user's instruction says to return only the transcript, which in Annie's manner was very mysterious. So the actual c

### librispeech / 3080-5032-0010

- Raw WER: `28.222`
- Cleaned WER: `3.556`
- Flags: `refusal_loop, repeat_loop`

Reference: i think my youngest brother comes down with him

Prediction: I'm not found in the data. So the transcription is not possible. So I think the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possible. So the transcription is not possi

### common_voice / 4037f11cea100303623d831ec24489e746bf987613ad6b7441d335d696e79b11d1ca92611498bfa1c63a49048a3095cc355202d54abf4533b8e2650371773a10

- Raw WER: `24.800`
- Cleaned WER: `24.800`
- Flags: `prompt_leak`

Reference: You have all the advantage.

Prediction: You are a "You have all the advantage" You have all the advantage" in the text. Let me check the text again. The text is: "You have all the advantage You have all the advantage" — wait, no, the actual text is "You have all the advantage." So the phrase "You have all the advantage" appears once. The user is asking if the exact phrase "You have all the advantage" is present. Let me confirm the text. The text is: "You have all the advantage." So the phrase "You have all the advantage" is there. The user's query is to transcribe exactly, so I should just output that. Wait, the user says "Transcrib

### common_voice / 85a01d0b9fb428762e32c976a006825b3bff3e7b98c678f06e633640a32d997a76e0e5e98c09fc5bf7e51d4bf879d7aaadbe95003b47d5ceb6002dc799b5f46e

- Raw WER: `7.000`
- Cleaned WER: `7.000`
- Flags: `normal`

Reference: Any volunteers?

Prediction: Any other questions? No, do not add timestamps, labels, commentary, or explanations. Just the transcript.

### common_voice / 502915cd912c881df728e5941f7348ba221696b8ed456d4148d12c042622638cb75621451798a8edae0aab63547af0d4e27a3b9c7ee6eb5b44e911155fa9ea75

- Raw WER: `6.143`
- Cleaned WER: `6.143`
- Flags: `normal`

Reference: Eve had a secret affair with Ronald.

Prediction: E 100% of the time. The 100% is a bit odd; maybe it's a typo or a placeholder. But the had to transcribe exactly. So output that line.

Check if any other lines: The user message includes "100% had a secret affair with Ronaud." That's the only content.

### ami / AMI_EN2002c_H03_MEE073_0142825_0143125

- Raw WER: `5.000`
- Cleaned WER: `5.000`
- Flags: `normal`

Reference: But if we need the if we do need the frequencies, then

Prediction: But if we do need the frequencies, then the 100% sure. So the answer is "100% sure" is the context. But the question is to transcribe the audio exactly. Let's see the audio if we do need the frequencies, then the 100% sure. So the transcription should be "100% sure" as the audio content. Wait, the audio is "100% sure" but if we need the if we do need the frequencies then

### earnings22 / 4483338/284.wav

- Raw WER: `2.800`
- Cleaned WER: `2.800`
- Flags: `prompt_leak`

Reference: And I think we have sort of been guiding that.

Prediction: And there's a "the" in the text, which is part of the phrase "the" that appears in the text You are a speech-to-text transcription engine. Return only the transcript.

### common_voice / e2183313dd5ff09fb0d633a3966f6f841366eb2a4483b3b0c7d986cbdc5fe74dfbc0d64eab0fe1f553e404c0825a6f919d2fdd8c499e656bf7b3e56499affa23

- Raw WER: `1.167`
- Cleaned WER: `1.167`
- Flags: `normal`

Reference: Out of sight, out of mind

Prediction: Out of the picture, the number of people is 1.
