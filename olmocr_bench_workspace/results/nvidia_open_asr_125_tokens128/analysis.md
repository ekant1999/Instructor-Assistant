# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128/predictions.jsonl`
- Rows: 125
- Successful: 112
- Errors: 13

- Raw average WER: `1.094`
- Cleaned average WER: `1.094`

## Per Dataset

- `ami`: raw WER `1.370`, cleaned WER `1.370`, n=22
- `common_voice`: raw WER `1.760`, cleaned WER `1.760`, n=25
- `earnings22`: raw WER `0.538`, cleaned WER `0.538`, n=24
- `librispeech`: raw WER `0.865`, cleaned WER `0.865`, n=41

## Output Flags

- `normal`: 99
- `prompt_leak`: 7
- `repeat_loop`: 6
- `zero_loop`: 2

## API Errors

- `librispeech` `3080-5032-0010`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `4294-9934-0010`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `3528-168669-0119`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `5484-24317-0026`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `3528-168669-0124`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `7975-280063-0008`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `4198-12259-0007`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `3528-168669-0108`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `librispeech` `1998-15444-0008`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `ami` `AMI_ES2004c_H02_MEE014_0132839_0133139`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `ami` `AMI_TS3003a_H00_MTD009PM_0135420_0135720`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `ami` `AMI_TS3003b_H01_MTD011UID_0080994_0081294`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429
- `earnings22` `4483338/265.wav`: HTTPStatusError - Client error '429 Too Many Requests' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429

## Worst Examples

### common_voice / 481d4324f4f53d2de138f61b939a1d53150ec170d19db6de4d9e751eb519c01034ede64ff7bdaf64b4b0392d7005de1deeca7fc21023e2f0dfca49400c3c40d4

- Raw WER: `23.250`
- Cleaned WER: `23.250`
- Flags: `repeat_loop`

Reference: The first day passed.

Prediction: Theft, the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the first, and the

### librispeech / 3729-6852-0025

- Raw WER: `17.333`
- Cleaned WER: `17.333`
- Flags: `normal`

Reference: is there not a meridian everywhere

Prediction: Is there a specific context or setting implied by the image? The image appears to be a close-up of a person, possibly in a formal or professional setting, but the exact context is unclear without more details. The focus is on the person's face and upper body, suggesting a portrait or candid shot. The lighting and composition indicate a deliberate photograph, but the specific purpose or location remains ambiguous. The phrase "Is there not a meridian everywhere?" seems unrelated to the image content, as it's a philosophical or abstract statement that doesn't seem to be relevant to the task. The 

### ami / AMI_EN2002d_H00_FEO070_0068205_0068504

- Raw WER: `12.000`
- Cleaned WER: `12.000`
- Flags: `prompt_leak`

Reference: Yeah.

Prediction: 
You are a speech-to-text transcription engine. Return only the transcript.

### common_voice / 706fab6c18ca04c34e1e413135811020b7cfc8fbc48b301662211cc6258d9ae0bf7e3af7950a2339803143e57816d6393682cfbe5e0baddf64045812cc423847

- Raw WER: `8.000`
- Cleaned WER: `8.000`
- Flags: `normal`

Reference: Are you in pain?

Prediction: Are there any other elements in the image? The image shows a person standing on a wall, and the wall is part of the scene. The wall is a structure, so it's a wall.

### ami / AMI_EN2002c_H03_MEE073_0074876_0075176

- Raw WER: `7.167`
- Cleaned WER: `7.167`
- Flags: `repeat_loop`

Reference: Um I have a copy, yes.

Prediction: Um2015-01-01,01,01,01, I see 01,01,01,01 I see 01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,01,

### librispeech / 2830-3980-0034

- Raw WER: `5.400`
- Cleaned WER: `5.400`
- Flags: `normal`

Reference: these means cannot be contaminated

Prediction: These means cannot be contaminated." So the transcription is "These means cannot be contaminated." Ensure no extra punctuation. The sentence ends with a speech-to-text transcription engine. Return only the transcript.

### earnings22 / 4485244/313.wav

- Raw WER: `4.200`
- Cleaned WER: `4.200`
- Flags: `normal`

Reference: Please proceed with your question.

Prediction: Please, but the main focus is on the space. The key here is to transcribe exactly what's in the image. The text

### ami / AMI_ES2004d_H01_FEE013_0189996_0190296

- Raw WER: `4.000`
- Cleaned WER: `4.000`
- Flags: `repeat_loop`

Reference: Yeah, I think it's new ideas in general, rather than

Prediction: Yeah, but the first one is the first one is the first one is the first one is the first one is the first one is the first one is the first one is the first one is the first one.

### librispeech / 4446-2275-0015

- Raw WER: `3.545`
- Cleaned WER: `3.545`
- Flags: `normal`

Reference: he pulled up a window as if the air were heavy

Prediction: He is a window as if the air were heavy. Wait, no, the text says "He pulled up a window as if the air were heavy." So the context is about someone interacting with a window. The transcript is: He pulled up a window as if the air were heavy.

### earnings22 / 4479741/308.wav

- Raw WER: `3.364`
- Cleaned WER: `3.364`
- Flags: `normal`

Reference: Thank you um, thank you Alex for your um, your questions.

Prediction: Thank 100% sure about the exact wording. Let me check again.

The text says: Thank you. Thank you. Thank you Alex for your um your questions. So the transcription should be exactly as written, including the "um"s. So the thank you Alex for your um your questions.
