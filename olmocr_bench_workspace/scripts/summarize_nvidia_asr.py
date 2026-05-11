#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from jiwer import wer


def normalize_for_wer(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_prediction(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\([^)]*(?:prompt|transcribe|audio|user|image|transcript)[^)]*\)", " ", text, flags=re.I)
    text = re.sub(r"You are a speech-to-text transcription engine\\.? Return only the transcript\\.?", " ", text, flags=re.I)
    text = re.sub(r"Transcribe this audio exactly\\.?", " ", text, flags=re.I)
    text = re.sub(r"Do not add timestamps, labels, commentary, or explanations\\.?", " ", text, flags=re.I)
    text = re.sub(r"\b(?:so the transcription is not possible\.?\s*){2,}", " ", text, flags=re.I)
    text = re.sub(r"\b0{8,}\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_prediction(text: str) -> list[str]:
    lower = text.lower()
    flags = []
    if not text.strip():
        flags.append("empty")
    if "you are a speech-to-text" in lower or "transcribe this audio" in lower or "the prompt says" in lower:
        flags.append("prompt_leak")
    if "the transcription is not possible" in lower:
        flags.append("refusal_loop")
    if re.search(r"0{20,}", text):
        flags.append("zero_loop")
    if re.search(r"(.{12,80})\1{3,}", text, flags=re.S):
        flags.append("repeat_loop")
    return flags or ["normal"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_jsonl")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    path = Path(args.predictions_jsonl)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    ok = [r for r in rows if r.get("status") == "ok"]
    errors = [r for r in rows if r.get("status") != "ok"]
    by_dataset = defaultdict(list)
    raw_by_dataset = defaultdict(list)
    flag_counts = Counter()
    bad_examples = []

    for r in ok:
        ref = normalize_for_wer(r.get("reference") or "")
        hyp_raw = r.get("prediction") or ""
        hyp_clean = normalize_for_wer(clean_prediction(hyp_raw))
        raw_wer = float(r.get("wer") or wer(ref, normalize_for_wer(hyp_raw)))
        cleaned_wer = wer(ref, hyp_clean) if ref else None
        r["cleaned_wer"] = cleaned_wer
        by_dataset[r["dataset"]].append(cleaned_wer)
        raw_by_dataset[r["dataset"]].append(raw_wer)
        for flag in classify_prediction(hyp_raw):
            flag_counts[flag] += 1
        if raw_wer > 1 or (cleaned_wer is not None and cleaned_wer > 1):
            bad_examples.append(r)

    lines = [
        "# NVIDIA Nemotron Omni ASR Analysis",
        "",
        f"- Predictions: `{path}`",
        f"- Rows: {len(rows)}",
        f"- Successful: {len(ok)}",
        f"- Errors: {len(errors)}",
        "",
    ]

    if ok:
        raw_avg = sum(float(r.get("wer") or 0) for r in ok) / len(ok)
        clean_vals = [float(r["cleaned_wer"]) for r in ok if r.get("cleaned_wer") is not None]
        clean_avg = sum(clean_vals) / len(clean_vals)
        lines += [
            f"- Raw average WER: `{raw_avg:.3f}`",
            f"- Cleaned average WER: `{clean_avg:.3f}`",
            "",
            "## Per Dataset",
            "",
        ]
        for dataset in sorted(by_dataset):
            raw_vals = raw_by_dataset[dataset]
            clean_dataset_vals = by_dataset[dataset]
            lines.append(
                f"- `{dataset}`: raw WER `{sum(raw_vals)/len(raw_vals):.3f}`, "
                f"cleaned WER `{sum(clean_dataset_vals)/len(clean_dataset_vals):.3f}`, n={len(raw_vals)}"
            )

    lines += ["", "## Output Flags", ""]
    for flag, count in flag_counts.most_common():
        lines.append(f"- `{flag}`: {count}")

    if errors:
        lines += ["", "## API Errors", ""]
        for r in errors:
            lines.append(f"- `{r.get('dataset')}` `{r.get('id')}`: {r.get('error_type')} - {r.get('error')}")

    lines += ["", "## Worst Examples", ""]
    for r in sorted(bad_examples, key=lambda item: float(item.get("wer") or 0), reverse=True)[:10]:
        lines += [
            f"### {r.get('dataset')} / {r.get('id')}",
            "",
            f"- Raw WER: `{float(r.get('wer') or 0):.3f}`",
            f"- Cleaned WER: `{float(r.get('cleaned_wer') or 0):.3f}`",
            f"- Flags: `{', '.join(classify_prediction(r.get('prediction') or ''))}`",
            "",
            f"Reference: {r.get('reference')}",
            "",
            f"Prediction: {(r.get('prediction') or '')[:600]}",
            "",
        ]

    output = Path(args.output) if args.output else path.with_name("analysis.md")
    output.write_text("\n".join(lines))
    print(output)


if __name__ == "__main__":
    main()
