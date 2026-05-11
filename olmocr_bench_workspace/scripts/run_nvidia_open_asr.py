#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import soundfile as sf
from datasets import Audio, load_dataset
from jiwer import wer


DEFAULT_DATASETS = [
    "librispeech:test.clean",
    "librispeech:test.other",
    "common_voice:test",
    "ami:test",
    "earnings22:test",
]

CONTENT_TYPES = {
    ".flac": "audio/flac",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def normalize_for_wer(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def dataset_spec(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise ValueError(f"Dataset spec must be config:split, got {spec!r}")
    config, split = spec.split(":", 1)
    return config, split


def extension_for_audio(path: str | None) -> str:
    suffix = Path(path or "").suffix.lower()
    if suffix in CONTENT_TYPES:
        return suffix
    return ".wav"


def prepare_audio_bytes(audio_bytes: bytes, source_ext: str) -> tuple[bytes, str, str]:
    if source_ext == ".flac":
        import io

        audio, samplerate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=False)
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio, samplerate, format="WAV", subtype="PCM_16")
        return wav_buffer.getvalue(), ".wav", "audio/wav"
    content_type = CONTENT_TYPES.get(source_ext, "audio/wav")
    return audio_bytes, source_ext, content_type


def create_asset(client: httpx.Client, api_key: str, content_type: str, description: str) -> tuple[str, str]:
    response = client.post(
        "https://api.nvcf.nvidia.com/v2/nvcf/assets",
        headers={
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"contentType": content_type, "description": description},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["assetId"], data["uploadUrl"]


def upload_asset(client: httpx.Client, upload_url: str, content_type: str, description: str, data: bytes) -> None:
    response = client.put(
        upload_url,
        content=data,
        headers={
            "Content-Type": content_type,
            "x-amz-meta-nvcf-asset-description": description,
        },
        timeout=180,
    )
    response.raise_for_status()


def delete_asset(client: httpx.Client, api_key: str, asset_id: str) -> None:
    response = client.delete(
        f"https://api.nvcf.nvidia.com/v2/nvcf/assets/{asset_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    if response.status_code not in {200, 202, 204, 404}:
        response.raise_for_status()


def make_audio_reference(
    client: httpx.Client,
    api_key: str,
    audio_bytes: bytes,
    content_type: str,
    description: str,
    inline_limit_bytes: int,
    keep_assets: bool,
) -> tuple[str, dict[str, Any]]:
    metadata: dict[str, Any] = {"content_type": content_type, "bytes": len(audio_bytes)}
    if len(audio_bytes) <= inline_limit_bytes:
        encoded = base64.b64encode(audio_bytes).decode("ascii")
        metadata["delivery"] = "inline"
        return f"data:{content_type};base64,{encoded}", metadata

    asset_id, upload_url = create_asset(client, api_key, content_type, description)
    upload_asset(client, upload_url, content_type, description, audio_bytes)
    metadata.update({"delivery": "asset", "asset_id": asset_id, "keep_asset": keep_assets})
    return f"data:{content_type};asset_id,{asset_id}", metadata


def transcribe(
    client: httpx.Client,
    api_key: str,
    server: str,
    model: str,
    audio_url: str,
    asset_id: str | None,
    max_tokens: int,
    retries: int,
    retry_sleep: float,
    prompt_style: str,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if asset_id:
        headers["NVCF-INPUT-ASSET-REFERENCES"] = asset_id

    if prompt_style == "strict":
        messages = [
            {
                "role": "system",
                "content": "/no_think",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe the spoken words in this audio. Return only the transcript.",
                    },
                    {"type": "audio_url", "audio_url": {"url": audio_url}},
                ],
            },
        ]
    elif prompt_style == "minimal":
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "/no_think\nTranscribe:"},
                    {"type": "audio_url", "audio_url": {"url": audio_url}},
                ],
            }
        ]
    elif prompt_style == "none":
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "audio_url", "audio_url": {"url": audio_url}},
                ],
            }
        ]
    elif prompt_style == "default":
        messages = [
            {
                "role": "system",
                "content": "/no_think\nYou are a speech-to-text transcription engine. Return only the transcript.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe this audio exactly. Do not add timestamps, labels, commentary, or explanations.",
                    },
                    {"type": "audio_url", "audio_url": {"url": audio_url}},
                ],
            },
        ]
    else:
        raise ValueError(f"Unknown prompt style: {prompt_style}")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2 if prompt_style == "strict" else 0,
        "max_tokens": max_tokens,
        "top_k": 1,
        "reasoning_budget": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    for attempt in range(retries + 1):
        response = client.post(
            server.rstrip("/") + "/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,
        )
        if response.status_code != 429:
            response.raise_for_status()
            break
        if attempt >= retries:
            response.raise_for_status()
        sleep_for = retry_sleep * (2**attempt)
        print(f"429 rate limit; sleeping {sleep_for:.1f}s before retry {attempt + 1}/{retries}")
        time.sleep(sleep_for)
    data = response.json()
    return data["choices"][0]["message"].get("content") or ""


def select_rows(config: str, split: str, samples: int, max_duration: float) -> list[dict[str, Any]]:
    dataset = load_dataset("hf-audio/open-asr-leaderboard", config, split=split, streaming=True)
    dataset = dataset.cast_column("audio", Audio(decode=False))

    selected = []
    for row in dataset:
        duration = float(row.get("audio_length_s") or 0)
        audio = row.get("audio") or {}
        audio_bytes = audio.get("bytes") or b""
        if not audio_bytes:
            continue
        if duration <= 0 or duration > max_duration:
            continue
        selected.append(row)
        if len(selected) >= samples:
            break
    return selected


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]
    load_dotenv(workspace / ".env")

    parser = argparse.ArgumentParser(description="Run a small NVIDIA Nemotron Omni ASR eval on Open ASR Leaderboard samples.")
    parser.add_argument("--datasets", nargs="+", default=DEFAULT_DATASETS, help="Dataset specs as config:split.")
    parser.add_argument("--samples-per-dataset", type=int, default=3)
    parser.add_argument("--max-duration", type=float, default=3.0)
    parser.add_argument("--inline-limit-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-sleep", type=float, default=3.0)
    parser.add_argument("--request-sleep", type=float, default=1.0)
    parser.add_argument("--prompt-style", choices=["default", "minimal", "strict", "none"], default="default")
    parser.add_argument("--output-dir", default=str(workspace / "results/nvidia_open_asr_smoke"))
    parser.add_argument("--keep-assets", action="store_true")
    args = parser.parse_args()

    server = os.environ.get("NVIDIA_SERVER", "").strip()
    model = os.environ.get("NVIDIA_MODEL", "").strip()
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not server or not model or not api_key:
        raise SystemExit("NVIDIA_SERVER, NVIDIA_MODEL, and NVIDIA_API_KEY must be set in .env or the environment")

    output_dir = Path(args.output_dir)
    audio_dir = output_dir / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    predictions_path = output_dir / "predictions.jsonl"
    report_path = output_dir / "report.md"
    if predictions_path.exists():
        predictions_path.unlink()

    records = []
    with httpx.Client() as client:
        preflight = client.get(server.rstrip("/") + "/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        preflight.raise_for_status()
        print(f"NVIDIA preflight OK: {preflight.status_code}")

        for spec in args.datasets:
            config, split = dataset_spec(spec)
            print(f"Selecting {args.samples_per_dataset} samples from {config}:{split}")
            rows = select_rows(config, split, args.samples_per_dataset, args.max_duration)
            if len(rows) < args.samples_per_dataset:
                print(f"Warning: selected only {len(rows)} samples from {config}:{split}")

            for idx, row in enumerate(rows, 1):
                audio = row["audio"]
                source_ext = extension_for_audio(audio.get("path"))
                audio_bytes, ext, content_type = prepare_audio_bytes(audio["bytes"], source_ext)
                sample_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(row.get("id") or idx))[:120]
                audio_path = audio_dir / config / f"{sample_id}{ext}"
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(audio_bytes)

                record = {
                    "dataset": config,
                    "split": split,
                    "id": row.get("id"),
                    "duration_s": row.get("audio_length_s"),
                    "audio_path": str(audio_path),
                    "reference": row.get("text") or "",
                }
                asset_id = None
                try:
                    audio_url, delivery = make_audio_reference(
                        client,
                        api_key,
                        audio_bytes,
                        content_type,
                        f"open-asr-{config}-{sample_id}",
                        args.inline_limit_bytes,
                        args.keep_assets,
                    )
                    asset_id = delivery.get("asset_id")
                    hyp = transcribe(
                        client,
                        api_key,
                        server,
                        model,
                        audio_url,
                        asset_id,
                        args.max_tokens,
                        args.retries,
                        args.retry_sleep,
                        args.prompt_style,
                    )
                    ref_norm = normalize_for_wer(record["reference"])
                    hyp_norm = normalize_for_wer(hyp)
                    record.update(
                        {
                            "status": "ok",
                            "prediction": hyp,
                            "wer": wer(ref_norm, hyp_norm) if ref_norm else None,
                            "delivery": delivery,
                        }
                    )
                    print(f"OK {config}:{sample_id} wer={record['wer']:.3f} delivery={delivery['delivery']}")
                except Exception as exc:
                    record.update({"status": "error", "error_type": type(exc).__name__, "error": str(exc)[:1000]})
                    print(f"ERR {config}:{sample_id} {type(exc).__name__}: {str(exc)[:160]}")
                finally:
                    if asset_id and not args.keep_assets:
                        try:
                            delete_asset(client, api_key, asset_id)
                        except Exception as exc:
                            record["asset_delete_error"] = str(exc)[:500]

                records.append(record)
                with predictions_path.open("a") as f:
                    f.write(json.dumps(record) + "\n")
                time.sleep(args.request_sleep)

    ok_records = [r for r in records if r.get("status") == "ok" and r.get("wer") is not None]
    lines = [
        "# NVIDIA Nemotron Omni ASR Smoke Report",
        "",
        f"- Model: `{model}`",
        f"- Dataset source: `hf-audio/open-asr-leaderboard`",
        f"- Output: `{output_dir}`",
        f"- Requested datasets: `{', '.join(args.datasets)}`",
        f"- Prompt style: `{args.prompt_style}`",
        f"- Successful samples: {len(ok_records)} / {len(records)}",
        "",
    ]
    if ok_records:
        avg_wer = sum(float(r["wer"]) for r in ok_records) / len(ok_records)
        lines += [f"- Average normalized WER: `{avg_wer:.3f}`", "", "## Per Dataset", ""]
        for config in sorted({r["dataset"] for r in ok_records}):
            subset = [r for r in ok_records if r["dataset"] == config]
            subset_wer = sum(float(r["wer"]) for r in subset) / len(subset)
            lines.append(f"- `{config}`: WER `{subset_wer:.3f}` over {len(subset)} samples")
    lines += ["", "## Files", "", f"- Predictions: `{predictions_path}`", f"- Audio cache: `{audio_dir}`", ""]
    report_path.write_text("\n".join(lines))
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
