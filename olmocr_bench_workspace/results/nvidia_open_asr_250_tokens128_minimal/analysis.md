# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_250_tokens128_minimal/predictions.jsonl`
- Rows: 500
- Successful: 496
- Errors: 4

- Raw average WER: `1.382`
- Cleaned average WER: `1.382`

## Per Dataset

- `ami`: raw WER `1.701`, cleaned WER `1.701`, n=97
- `common_voice`: raw WER `1.402`, cleaned WER `1.402`, n=100
- `earnings22`: raw WER `1.462`, cleaned WER `1.462`, n=99
- `librispeech`: raw WER `1.177`, cleaned WER `1.177`, n=200

## Output Flags

- `normal`: 458
- `repeat_loop`: 35
- `zero_loop`: 5
- `prompt_leak`: 1
- `empty`: 1

## API Errors

- `ami` `AMI_IS1009a_H00_FIE088_0074169_0074465`: ReadTimeout - The read operation timed out
- `ami` `AMI_ES2004b_H01_FEE013_0155203_0155496`: ReadTimeout - The read operation timed out
- `ami` `AMI_IS1009a_H00_FIE088_0013804_0014097`: ReadTimeout - The read operation timed out
- `earnings22` `4450488/234.wav`: ReadTimeout - The read operation timed out

## Worst Examples

### ami / AMI_TS3003c_H00_MTD009PM_0098483_0098778

- Raw WER: `98.000`
- Cleaned WER: `98.000`
- Flags: `repeat_loop`

Reference: Okay.

Prediction: Okay, so the second part of 1 is 1 Okay, so the second part of 1 is 1. So we have a 1 in the second part of 1. So we have a 1 in the second part of 1. So we have a 1 in the second part 1. So we have a 1 in the second part 1. So we have a 1 in the second part 1. So we have a 1 in the second part 1. So we have a 1 in the second part 1. So we have a 1 in the second part

### common_voice / 91e6994572f2793ccfc4e74ce4f5c924563d1f5f1cfd0debc4a7c33456225142f82bb516453202fa593ba893ca20e99bcd68f376f58c417ff8f02364befedea6

- Raw WER: `33.667`
- Cleaned WER: `33.667`
- Flags: `normal`

Reference: Allies and partners.

Prediction: All right, let's check the text again. The text is "All right, let's check the text again." So, let's verify the transcription.

The image shows a person with short dark hairy hair, wearing a dark top, against a plain background. The lighting is somewhat dim and cool-toned. The person is facing the camera directly. The background is a plain, light-colored wall, possibly with a slight texture or reflection.

The prompt asks to the model to "Transcribe" the image. This means I need to transcribe the visible text or describe the scene if there is no text. Since there is no

### earnings22 / 4485244/102.wav

- Raw WER: `25.000`
- Cleaned WER: `25.000`
- Flags: `repeat_loop`

Reference: The first is our potential.

Prediction: The first is the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first of the first

### earnings22 / 4479741/307.wav

- Raw WER: `24.000`
- Cleaned WER: `24.000`
- Flags: `normal`

Reference: Thanks.

Prediction: Thanks for the detailed response. The word "Thanks" is used in the context of a response to a previous message. So "Thanks" is a separate

### librispeech / 5764-299665-0045

- Raw WER: `23.000`
- Cleaned WER: `23.000`
- Flags: `normal`

Reference: has christianity done good

Prediction: HasChristianity done good? Wait, the original sentence is "Has Christianity done good?" So the transcription should be exactly that.

Wait, the user says "Transcribe:" so I need to transcribe the given text exactly as it is. Let me check the input again.

The input is:

"Has Christianity done good?"

So the task is to transcribe that exact string. So the answer should be "Has Christianity done good?" without any changes.

Wait, but the user says Has says "Transcribe:" so the correct output is the exact text provided. Let me confirm.

The user message is:

"Transcribe: Has

### common_voice / 706fab6c18ca04c34e1e413135811020b7cfc8fbc48b301662211cc6258d9ae0bf7e3af7950a2339803143e57816d6393682cfbe5e0baddf64045812cc423847

- Raw WER: `20.500`
- Cleaned WER: `20.500`
- Flags: `normal`

Reference: Are you in pain?

Prediction: Are there any parts that are not transcribed? The instruction says "Transcribe:" so we need to output exactly what's in the text. The text is "Are you in pain?" So we need to output that. But the user says "Transcribe:" so we need to output the transcription. So the answer should be "Are you in pain?" But are you in pain? Wait, the text is "Are you in pain?" So the transcription is that. So the answer is it a great? Are you in a page?

### common_voice / 88ec956dc47c617d26c5be3ef383efa28bb6568f4b00765bef0dd12c00049fdde684bfc499a33395b8170c5d2257c67fafbceb5009e9a9f0a0b709552149386e

- Raw WER: `19.667`
- Cleaned WER: `19.667`
- Flags: `normal`

Reference: It occurs worldwide.

Prediction: It seems I made a mistake. Let me redo properly.

We need to transcribe the given text: "It occurs worldwide."

So the transcription should be exactly that string, no extra punctuation or spaces. The text is "It occurs worldwide."

Check: The user says "Transcribe:" then the text. So answer should be "It occurs worldwide."

Make sure no extra characters. It occurs worldwide.

### librispeech / 8188-269288-0052

- Raw WER: `16.600`
- Cleaned WER: `16.600`
- Flags: `repeat_loop`

Reference: annie's manner was very mysterious

Prediction: Annie's manner was very mysterious." -> Wait, the text says "Annie's manner was very mysterious." in the prompt? No, the prompt is "Transcribe:". The image content Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Annie's manner was very mysterious. Anni

### librispeech / 3528-168669-0026

- Raw WER: `16.286`
- Cleaned WER: `16.286`
- Flags: `repeat_loop`

Reference: no did you not hear the bell

Prediction: No, the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context is that the context No. context is that the context is that the context is that the context is incorrect because it's too broad. It's too broad. It's too broad. It's too broad. It's too broad. It

### earnings22 / 4483338/601.wav

- Raw WER: `15.875`
- Cleaned WER: `15.875`
- Flags: `repeat_loop`

Reference: So yes, you need campaigns to drive it.

Prediction: So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the So the
