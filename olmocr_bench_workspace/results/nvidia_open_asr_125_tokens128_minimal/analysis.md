# NVIDIA Nemotron Omni ASR Analysis

- Predictions: `Instructor-Assistant/olmocr_bench_workspace/results/nvidia_open_asr_125_tokens128_minimal/predictions.jsonl`
- Rows: 125
- Successful: 125
- Errors: 0

- Raw average WER: `1.142`
- Cleaned average WER: `1.125`

## Per Dataset

- `ami`: raw WER `1.421`, cleaned WER `1.361`, n=25
- `common_voice`: raw WER `1.162`, cleaned WER `1.162`, n=25
- `earnings22`: raw WER `1.418`, cleaned WER `1.418`, n=25
- `librispeech`: raw WER `0.854`, cleaned WER `0.842`, n=50

## Output Flags

- `normal`: 116
- `repeat_loop`: 9
- `zero_loop`: 2

## Worst Examples

### common_voice / 83b0b98d8a29e344f81eee60ce2e3f652383c5837e9da37fc15f5a68d921faf54ecda13a018210a93353d1c4753383e5b0eb44f66c7c47c2e00f0964bbcdae30

- Raw WER: `19.167`
- Cleaned WER: `19.167`
- Flags: `repeat_loop`

Reference: He is certified to handle food.

Prediction: He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person who is not a threat to others. He is a person

### earnings22 / 4485244/313.wav

- Raw WER: `18.600`
- Cleaned WER: `18.600`
- Flags: `normal`

Reference: Please proceed with your question.

Prediction: Please 
The question: "Please proceed with your question." The context: "Please proceed with your question." Wait the user says: "Please proceed with your question." That's ambiguous. The instruction: "Please proceed with your question." Possibly they want me to ask a question? Or they want me to proceed with answering a question? The context is just "Please proceed with your question." That's not a question. Maybe they want me to ask a question? Or they want me to respond with your question? The instruction says: "Please proceed with your question." That seems like a prompt to ask a question.

### ami / AMI_EN2002c_H03_MEE073_0074876_0075176

- Raw WER: `10.833`
- Cleaned WER: `10.833`
- Flags: `repeat_loop`

Reference: Um I have a copy, yes.

Prediction: Um, which is the same as the one we are using for the 2015? The 2015? The 2015? The 2015? The 2015? The 2015? The 2015? The 2015? The 2015? The 2015? Wait, no. Let's check the actual image content. The image shows a person with a blurred face, wearing a dark shirt, and the background is a plain, light-colored wall. There's no visible text, no

### earnings22 / 4432298/81.wav

- Raw WER: `10.000`
- Cleaned WER: `10.000`
- Flags: `repeat_loop`

Reference: Simplified cash flow presentation.

Prediction: sim 100% accurate. The 100% is a bit odd, but it's the 100% that is being asked for 100% of the time. So the 100% is the 100% of the 100% of the 100% of the 100% of the 100%

### ami / AMI_EN2002d_H01_FEO072_0173882_0174181

- Raw WER: `8.364`
- Cleaned WER: `8.364`
- Flags: `repeat_loop`

Reference: And then if you, I don't know, double-click on one

Prediction: And the second part of the second part is "on one". So the second part empty (no second part). So second part = "" (empty string). But spec says second part is optional; if none, maybe empty string. We'll output "".

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.

Second part empty.



### librispeech / 8188-269288-0052

- Raw WER: `7.600`
- Cleaned WER: `7.600`
- Flags: `repeat_loop`

Reference: annie's manner was very mysterious

Prediction: Annot An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An An Anny's manner was very mysterious.

### librispeech / 4294-9934-0010

- Raw WER: `7.600`
- Cleaned WER: `7.600`
- Flags: `repeat_loop`

Reference: they soon elbowed him abruptly

Prediction: They are looking for a way to see if the 2019-04- 2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019-04-2019

### librispeech / 3729-6852-0021

- Raw WER: `7.000`
- Cleaned WER: `7.000`
- Flags: `normal`

Reference: i thank him and take my leave

Prediction: I am not sure if I should use the full stop at the end of the sentence or not. What do you think?

Let me check again. The question is about whether to use a full stop (period) at the end of the sentence. The sentence in question is "I thank him, and take my leave.

### common_voice / 1729e64068b79bbd061feb505a02cdb70dde4ea18f463fd57b3d25032eb5ac8f20e12f5d68c52754cd47f0919c96813ac40cb9f086862bbc75e2aee813b3cfb7

- Raw WER: `6.167`
- Cleaned WER: `6.167`
- Flags: `repeat_loop`

Reference: I wasn't a radical at all.

Prediction: I
 10.0.0. I 0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0. I wasn't a radical at all.

### librispeech / 7902-96594-0000

- Raw WER: `5.667`
- Cleaned WER: `5.667`
- Flags: `normal`

Reference: seemed in good spirits last night mister gurr eh

Prediction: Se 100% sure about the exact details of the image, but based on the provided text, I can infer the following:

- The image likely to be described is likely a photograph or a visual scene.
- The main subject is "the image" (which is not specified, so I'll assume it's a general
