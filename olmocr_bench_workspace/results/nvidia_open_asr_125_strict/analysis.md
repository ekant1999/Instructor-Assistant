# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_strict/predictions.jsonl`
- Rows: 125
- Successful: 124
- Errors: 1

- Raw average WER: `0.783`
- Cleaned average WER: `0.783`

## Per Dataset

- `ami`: raw WER `0.555`, cleaned WER `0.555`, n=25
- `common_voice`: raw WER `0.539`, cleaned WER `0.539`, n=25
- `earnings22`: raw WER `0.153`, cleaned WER `0.153`, n=25
- `librispeech`: raw WER `1.345`, cleaned WER `1.345`, n=49

## Output Flags

- `normal`: 120
- `repeat_loop`: 4
- `zero_loop`: 1

## API Errors

- `librispeech` `237-134493-0009`: ReadTimeout - The read operation timed out

## Worst Examples

### librispeech / 8131-117029-0002

- Raw WER: `15.333`
- Cleaned WER: `15.333`
- Flags: `normal`

Reference: only gordon and sheila were left

Prediction: Only Gordon and 100% accurate. So I need to transcribe exactly what's in the image. The image has the text "Only Gordon and Sheila were left." So the transcription should be that exact sentence.

Wait, the user provided an image, but in the context, the image is represented as a text block. Wait, looking back, the user's message is just the image, but in the problem setup, the assistant is supposed to process it. However, in this case, the actual content Sheila were left. 

Wait, the user's input is an image, but in the problem description, the assistant

### librispeech / 260-123286-0014

- Raw WER: `13.000`
- Cleaned WER: `13.000`
- Flags: `normal`

Reference: truly this sea is of infinite width

Prediction: Tr 1.5 hours ago, so it's recent. The text is "Truly the sea is of infinite width." So the transcription is straightforward.

I need to make surely the transcription exactly as spoken. Let me check the punctuation. The original text has a period at the end. So the transcription should be "Truly the sea is of infinite width." with a period.

Wait, the user said "Transcribe the spoken words", so I should just write the exact words. Let me confirm: "Truly the sea is of infinite width." Yes, that's what's in the text.

No need for

### librispeech / 1995-1837-0006

- Raw WER: `12.714`
- Cleaned WER: `12.714`
- Flags: `normal`

Reference: the world was water veiled in mists

Prediction: The word "the" is "the" is "the" (the second "the" is the first "the" in the text). So we need to find the word "the" in the text. It appears that "the" is the first word of the text. So we need to find the word "the" in the text. It is 1st word. So we  need to find the word "the"the" in the text. It appears that "the" is the first word of the text. So we need to find the word "the" in the text. It is 1st

### librispeech / 8280-266249-0057

- Raw WER: `8.700`
- Cleaned WER: `8.700`
- Flags: `normal`

Reference: it was the last game of cards for that trip

Prediction: It's a very short sentence, but it's all we have. Let's see the full text: "It's a very short sentence, It's a very short sentence" Let's check if there's more. Let's assume the text is: "It's a very short sentence" and the second line is "It's a very short sentence". Let's see if there's a third line. Let's assume the text is: "It's a very short sentence" and then "It's a very short sentence" again. Let's assume the text is: "It's a very short sentence" and then "It

### ami / AMI_EN2002c_H02_MEE071_0041434_0041734

- Raw WER: `7.583`
- Cleaned WER: `7.583`
- Flags: `normal`

Reference: So then does this how does is how is this box populated?

Prediction: So, 'So, the question is asking how the box is not being visible affects the answer. The original answer was "So then does this how does this how is this box populated? Populated?" which seems like a misphrased question. The user is pointing out that the box isn't visible, so the question. So the key point is that since the box. So the answer should be that the box isn't visible, so the question about the box being populated is irrelevant. Therefore, the correct response is to state that the box is populated question is not answerable because the box isn't visible.

### librispeech / 7975-280063-0008

- Raw WER: `5.727`
- Cleaned WER: `5.727`
- Flags: `repeat_loop`

Reference: they did mark my clothes in one or two places however

Prediction: They need. They did mark my clothes in one or two places, however, need. They did mark my clothes in one or two places, however. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need. need

### ami / AMI_ES2004b_H02_MEE014_0151424_0151723

- Raw WER: `4.200`
- Cleaned WER: `4.200`
- Flags: `repeat_loop`

Reference: Yeah, speech recognition, but yeah.

Prediction: Yeah 100% sure about that. The 100% sure about that. The 100% sure about that. The 100% sure about that. The 100100% speech recognition but yeah.

### librispeech / 7902-96594-0000

- Raw WER: `3.889`
- Cleaned WER: `3.889`
- Flags: `normal`

Reference: seemed in good spirits last night mister gurr eh

Prediction: Seemed in good spirits last night, Mr. Garr, eh?" - this is the text of the audio.
- The audio is a spoken sentence: "Seemed in good spirits last night, Mr. Garr, eh?" - this is the text of the audio.

The audio is a

### common_voice / 83b0b98d8a29e344f81eee60ce2e3f652383c5837e9da37fc15f5a68d921faf54ecda13a018210a93353d1c4753383e5b0eb44f66c7c47c2e00f0964bbcdae30

- Raw WER: `2.833`
- Cleaned WER: `2.833`
- Flags: `normal`

Reference: He is certified to handle food.

Prediction: He is certified to handle food. 
Let me check again. The spoken words in the audio are 'He is certified to handle food'.

### common_voice / 17b70dcbb65a416800533938b54d423bbdd2255252734df79e004b3fe99de3244d656bc3949e15a17600c7edcfdeac82b280907307fe1000a252b4ea91c8f4ed

- Raw WER: `2.600`
- Cleaned WER: `2.600`
- Flags: `normal`

Reference: The head is pear shaped.

Prediction: The head is pear-shaped. So the main subject is the head. The head is the main focus.
