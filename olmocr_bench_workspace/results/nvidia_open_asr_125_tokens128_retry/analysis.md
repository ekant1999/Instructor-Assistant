# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_retry/predictions.jsonl`
- Rows: 125
- Successful: 124
- Errors: 1

- Raw average WER: `1.044`
- Cleaned average WER: `1.044`

## Per Dataset

- `ami`: raw WER `0.345`, cleaned WER `0.345`, n=25
- `common_voice`: raw WER `1.637`, cleaned WER `1.637`, n=25
- `earnings22`: raw WER `1.910`, cleaned WER `1.910`, n=25
- `librispeech`: raw WER `0.655`, cleaned WER `0.655`, n=49

## Output Flags

- `normal`: 112
- `repeat_loop`: 7
- `prompt_leak`: 5
- `zero_loop`: 2

## API Errors

- `librispeech` `8455-210777-0026`: ReadTimeout - The read operation timed out

## Worst Examples

### earnings22 / 4432298/81.wav

- Raw WER: `12.750`
- Cleaned WER: `12.750`
- Flags: `repeat_loop`

Reference: Simplified cash flow presentation.

Prediction: simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text: "simplified text

### common_voice / 7b8b6766cc85e2a4f65b0b3545ee403b8a775b1d2ca7de844b58be7e9f28e02d8c2d99dbb9d1d9898b0e1152aa65488881484f3a25e7790afb0ea159da23486c

- Raw WER: `12.375`
- Cleaned WER: `12.375`
- Flags: `repeat_loop`

Reference: I was near the cabin, and saw you.

Prediction: I think we need to add the transcript: I think we need to add: "I think we need to add the transcript: I think we need to add the transcript: I think we need to add: "I think we need to add: "I think we need to add: "I think we need to add: I think we need to add: "I think we need to be careful.

Let's produce final answer: "I think we need to add: "I think we need to add: "I think we need to add: "I think we need to add: "I think we need to add:

### earnings22 / 4450488/234.wav

- Raw WER: `11.222`
- Cleaned WER: `11.222`
- Flags: `prompt_leak`

Reference: It needs to transform both in the context of…

Prediction: It seems like the user is asking to transcribe the audio exactly, but the provided text is not a transcription of the audio; it's a description of what the system should do. The instruction says: "You are a speech-to-text transcription engine. Return only the transcript." So I need to output the transcript of the audio needs to transform both in the context of. But the given text is not the transcript; it's a description. The actual transcript likely is "It needs to transform both in the context of". So I should output that exact phrase. Probably the transcript is "It needs to transform both i

### librispeech / 8280-266249-0057

- Raw WER: `9.200`
- Cleaned WER: `9.200`
- Flags: `normal`

Reference: it was the last game of cards for that trip

Prediction: It's a simple "Hello" but maybe they want to say "Hello" to the user. So they need to say "Hello" to the user. So they need to say "Hello" to the user. So they were the last game over cards for that trip. So maybe they need to say "Hello" to the user. So they need to say "Hello" to the user. So they played cards for that trip. So maybe they need to say "Hello" to the user. So they need to say "Hello" to the user. So they need to say "Hello" to the user. So they

### common_voice / 481d4324f4f53d2de138f61b939a1d53150ec170d19db6de4d9e751eb519c01034ede64ff7bdaf64b4b0392d7005de1deeca7fc21023e2f0dfca49400c3c40d4

- Raw WER: `8.750`
- Cleaned WER: `8.750`
- Flags: `repeat_loop`

Reference: The first day passed.

Prediction: The first line is "The first line is 'The first line is 'The first line is "The first line is 'The first line is 'The first line is 'The first line is 'The first lay pass him.

### librispeech / 1998-15444-0008

- Raw WER: `8.375`
- Cleaned WER: `8.375`
- Flags: `prompt_leak`

Reference: the dose for an adult is ten minims

Prediction: The prompt says "Do not add timestamps, labels, commentary, or an explanations." So just the text.

Let's re-read the first image content: "You are a speech-to-text transcription. Return only the transcript."
The second image is the actual request: "Transcribe this audio exactly. Do not add timestamps, labels, commentary, or explanations."

So I need to output the text found in the audio.
Audio content: "The dose for an adult is ten minimums.

### earnings22 / 4485244/161.wav

- Raw WER: `7.133`
- Cleaned WER: `7.133`
- Flags: `repeat_loop`

Reference: You may press star two if you'd like to remove your question from the queue.

Prediction: You are a re a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the initial text is "You are a text input field, but the

### librispeech / 672-122797-0053

- Raw WER: `6.800`
- Cleaned WER: `6.800`
- Flags: `normal`

Reference: they were so extremely curious

Prediction: They were so extremely curious" which seems like a mix of transcription and maybe a typo. Wait, looking back, the user's last message was "They were so extremely curious" which was the input to transcribe. But in the current

### earnings22 / 4450488/362.wav

- Raw WER: `6.667`
- Cleaned WER: `6.667`
- Flags: `normal`

Reference: I think that our CEO has already answered the question of Mr.

Prediction: I don't see a building, just a person speaking. The background is indistinct/blurry. It looks like a convention center hall. The background is out of focus. It's hard to say definitively "This is a building". It think the key is whether the location is identifiable. Here, it's likely a convention center, but is it *visible* enough? The Patten, our CEO... suggests a1 a1 a1 a1 a1 a1 a1 a1 a1 a1 a1 a question a1 a1 a1 a1 a1 a1 a1 a1 a1 a

### common_voice / 502915cd912c881df728e5941f7348ba221696b8ed456d4148d12c042622638cb75621451798a8edae0aab63547af0d4e27a3b9c7ee6eb5b44e911155fa9ea75

- Raw WER: `6.571`
- Cleaned WER: `6.571`
- Flags: `repeat_loop`

Reference: Eve had a secret affair with Ronald.

Prediction: E2022, and the 2022 is the 2022. The 2022 is the 2022. The 2022 is the 2022. The 2022 is the 2022. The 2022 is the 2022. The 2022 is the 2022. The 2022 is the 2022. The 2022 is the 2022. The 2022 is the 
