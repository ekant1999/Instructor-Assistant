# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_500_strict/predictions.jsonl`
- Rows: 500
- Successful: 491
- Errors: 9

- Raw average WER: `0.990`
- Cleaned average WER: `0.990`

## Per Dataset

- `ami`: raw WER `0.787`, cleaned WER `0.787`, n=99
- `common_voice`: raw WER `1.180`, cleaned WER `1.180`, n=98
- `earnings22`: raw WER `1.070`, cleaned WER `1.070`, n=98
- `librispeech`: raw WER `0.957`, cleaned WER `0.957`, n=196

## Output Flags

- `normal`: 465
- `repeat_loop`: 23
- `zero_loop`: 4
- `empty`: 1

## API Errors

- `librispeech` `3729-6852-0025`: HTTPStatusError - Server error '500 Internal Server Error' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500
- `librispeech` `4446-2273-0012`: ReadTimeout - The read operation timed out
- `librispeech` `3729-6852-0010`: HTTPStatusError - Server error '502 Bad Gateway' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502
- `librispeech` `1688-142285-0015`: ReadTimeout - The read operation timed out
- `common_voice` `85a01d0b9fb428762e32c976a006825b3bff3e7b98c678f06e633640a32d997a76e0e5e98c09fc5bf7e51d4bf879d7aaadbe95003b47d5ceb6002dc799b5f46e`: RemoteProtocolError - Server disconnected without sending a response.
- `common_voice` `119ec9ce235cfdf85a17841f27a918465e6f0643a3eb480c570490ab74cdbfcaf9aa75846e6c950266f2eeec0527e170d4fde3b4c7f0c6a231248aa3ddc5ff14`: ReadTimeout - The read operation timed out
- `ami` `AMI_IS1009a_H00_FIE088_0074169_0074465`: ReadTimeout - The read operation timed out
- `earnings22` `4483338/205.wav`: ReadTimeout - The read operation timed out
- `earnings22` `4485244/102.wav`: ReadTimeout - The read operation timed out

## Worst Examples

### common_voice / fc8847590eb211d61bc0ac7414956696df2aaebf2fea31a43043169d28eca9dc87572810414f658383cb6ee27f44c4ef311fd5bba6cb0e2cd24b0a86f85158b3

- Raw WER: `21.500`
- Cleaned WER: `21.500`
- Flags: `normal`

Reference: What can it mean?

Prediction: What is the purpose of the "What is the purpose of the meaning?" question? It seems to be asking about the meaning of the word "meaning" itself. It's a philosophical question about the concept of meaning. It's a bit abstract. It's not about a specific context. It's about the concept of meaning in general. It's a question that can be answered in different ways, depending on the perspective. It's a question that can be answered with a definition, an explanation of the purpose of meaning. It's a question

### librispeech / 3575-170457-0018

- Raw WER: `21.000`
- Cleaned WER: `21.000`
- Flags: `repeat_loop`

Reference: sir march sixteenth

Prediction: Sirest1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,

### earnings22 / 4432298/95.wav

- Raw WER: `17.333`
- Cleaned WER: `17.333`
- Flags: `normal`

Reference: Please go ahead.

Prediction: Please continue thinking
We need to transcribe the spoken words in the audio.
The user wants me to transcribe the spoken words in the audio. The user wants me to transcribe the spoken words in the audio. The spoken words in the audio. The user wants to transcribe the spoken words in please go ahead.

### common_voice / 399f473f77547eb8e9ac835d1521c5098f87ea81a74db9afc46e1036be71fdfc0d5601b71138e908d91e3d3d6da507ee68aa1a409627107206d33f9e2a288ffc

- Raw WER: `16.167`
- Cleaned WER: `16.167`
- Flags: `normal`

Reference: What on earth do you mean?

Prediction: What  What is the question? The user says: "What on earth do you mean?" Probably they ask "What on earth do you mean?" Or "What on earth do you mean?" The context: they ask "What on earth do you mean?" So they want clarification. We need to respond asking for clarification? Or what is the question? The user asks "What on earth do you mean?" That's ambiguous. Could be they are asking what the assistant mean of mine is? Or they ask "What on earth do you mean?" maybe they want explanation of something. Since no context, we need to ask for clarification.

### earnings22 / 4450488/120.wav

- Raw WER: `15.667`
- Cleaned WER: `15.667`
- Flags: `repeat_loop`

Reference: We simply have to stock up…

Prediction: We simply have to check for the presence of the we simply have to check for the presence of the word "we" in the text. So, the word "we" appears to check for the presence of the word "we" in the text. So, the word "we" to check for the presence of the word "we" in the text. So, the word "we" to check for the presence of the word "we" in the text. So, the word "we" to check for the presence of the word "we" in the text. So, the word "we" to check for the

### librispeech / 1998-29455-0004

- Raw WER: `15.500`
- Cleaned WER: `15.500`
- Flags: `normal`

Reference: oh look said dickie the flowers

Prediction: Oh, the user's instruction says to transcribe the spoken words, so I need to check if the audio contains the actual spoken words Oh, look said Dicky, the flowers. So the audio is just that sentence. So the actual spoken words are "Oh, look, said Dicky, the flowers." So the transcript is just that.

Wait, the user says "Transcribe the spoken words in this audio. Return only the transcript." So the audio is the spoken words, which is "Oh, look, said Dicky, the flowers." So the transcript is just that sentence.

Wait, the user provided a JSON with

### common_voice / 28799bba44202244981813a090e29ddbbc791acd18f7405c91977ed66b3fc623cae9394a5d9bf90a2e9ff5bfcc675c6fe1b117b3dc7a894e54f4a3023f139e12

- Raw WER: `14.667`
- Cleaned WER: `14.667`
- Flags: `repeat_loop`

Reference: Shake hands with this friendly child.

Prediction: Shake hands with "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test." and "This is a test

### common_voice / 94e170972c384280165fabefb2fb442a3f58bf64cc8fddc04173eb78e4d9a1d35c0e6b5e84b4cd340f62520c17a3ab1369ae2d13ed6bdcf74e77d66b9f15deb6

- Raw WER: `14.000`
- Cleaned WER: `14.000`
- Flags: `repeat_loop`

Reference: Who has already arrived?

Prediction: Who has already arrived? The question is "Who has already arrived?" So the spoken words are "Who has already arrived?" So the transcript is "Who has already arrived?" So the transcript is "Who has already arrived?" So the transcript is "Who has already arrived?" So the transcript is "Who has already arrived?" So the transcript is "Who has already arrived

### common_voice / 3740ce6b920773dd184361365221851edb361fef99c8f90ab0adb7c5451041ce619b4fa77b1510fb355bbe392185b7cfbaf046197ee89ccf62800816efec304a

- Raw WER: `13.500`
- Cleaned WER: `13.500`
- Flags: `normal`

Reference: This was too much.

Prediction: This was too much too long. Maybe the command was incorrect. Let me check the user's message says "This was too long time 1: too much." which might be a typo. Maybe the actual command was "This was too much." Wait, but maybe the user wrote "This was too much. Let me check the actual command.

Wait, maybe

### ami / AMI_ES2004d_H02_MEE014_0020371_0020670

- Raw WER: `13.286`
- Cleaned WER: `13.286`
- Flags: `repeat_loop`

Reference: how do you say, it's yeah yeah

Prediction: How to find the difference between two and two? (1) The difference between two and two? (2) The difference between two and two and two? (1) The difference between two and two? (3) The difference between two and two? (3) The difference between two and two? (3) The difference between two and two? (3) The difference between two and two? (3) The difference between two and two? How to find the difference between two and two? (3) The difference between two and two? (3) The difference between two and two? (3) The difference between
