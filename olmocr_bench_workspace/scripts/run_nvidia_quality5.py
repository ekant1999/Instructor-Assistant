import asyncio
import json
import os
from pathlib import Path

from olmocr.bench.runners.run_server import run_server


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "olmocr_bench_workspace/data/olmOCR-bench/bench_data"
OUT_ROOT = ROOT / "olmocr_bench_workspace/data/olmOCR-bench/bench_data_nvidia_quality5_v2"
CANDIDATE = os.environ.get("NVIDIA_CANDIDATE", "nemotron_omni_nvidia_ocr")
PROMPT_TEMPLATE = os.environ.get("NVIDIA_PROMPT_TEMPLATE", "nvidia_ocr")
OUT_DIR = OUT_ROOT / CANDIDATE

PDFS = [
    BENCH / "pdfs/tables/022b5843eb82c5e76fb3da69a0c432187f6c_pg1_pg1.pdf",
    BENCH / "pdfs/headers_footers/9d07f23e6fc4711287168667d2daf3b2f5ac6bb2_page_1.pdf",
    BENCH / "pdfs/multi_column/028649690bbc67fe3ba040b4b2bf6c37f487_page_29_pg1.pdf",
    BENCH / "pdfs/tables/00e980a0c4645fc83f27c467d10bbdeb8661_pg64.pdf",
    BENCH / "pdfs/headers_footers/0805b42e6e18b9c2f2f3d31d8ecf73e1a422f182_page_2_processed.pdf",
]


async def convert_one(pdf: Path) -> dict:
    rel = pdf.relative_to(BENCH / "pdfs")
    output = OUT_DIR / rel.with_suffix(".md")
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"RUN {rel}", flush=True)

    record = {"pdf": str(pdf), "relative_pdf": str(rel), "output": str(output)}
    try:
        text = await asyncio.wait_for(
            run_server(
                str(pdf),
                endpoint_env="NVIDIA_SERVER",
                api_key_env="NVIDIA_API_KEY",
                model=os.environ["NVIDIA_MODEL"],
                prompt_template=PROMPT_TEMPLATE,
                response_template="plain",
                target_longest_image_dim=1024,
                image_format="jpeg",
                jpeg_quality=85,
                max_tokens=4096,
                enable_thinking="false",
                allow_non_stop="true",
            ),
            timeout=120,
        )
        output.write_text(text or "")
        record.update({"status": "ok", "chars": len(text or "")})
        print(f"OK {rel} chars={record['chars']}", flush=True)
    except Exception as exc:
        output.write_text("")
        record.update(
            {
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "chars": 0,
            }
        )
        print(f"ERR {rel} {type(exc).__name__}: {str(exc)[:160]}", flush=True)
    return record


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"CANDIDATE {CANDIDATE}")
    print(f"PROMPT_TEMPLATE {PROMPT_TEMPLATE}")
    manifest = []
    for pdf in PDFS:
        manifest.append(await convert_one(pdf))

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT_ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"MANIFEST {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
