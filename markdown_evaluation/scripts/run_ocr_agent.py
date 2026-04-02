from __future__ import annotations

import argparse
import multiprocessing as mp
import shutil
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from markdown_evaluation.scripts._common import (
    RUN_DIR,
    BenchmarkDoc,
    ensure_dirs,
    select_docs,
    system_doc_dir,
    system_root,
    write_json,
    write_jsonl,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hybrid ocr_agent extractor for benchmark documents.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument("--ocr-server", help="Optional OCR/VLM server URL used by ocr_agent.")
    parser.add_argument("--ocr-model", default="allenai/olmOCR-2-7B-1025-FP8")
    parser.add_argument("--ocr-workspace", default="./tmp_ocr")
    parser.add_argument("--use-pdf-page-ocr", action="store_true", default=False)
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Per-document timeout for ocr_agent extraction.")
    parser.add_argument("--overwrite", action="store_true", default=False)
    return parser


def _count_assets(doc_dir: Path, doc_id: str) -> Dict[str, int]:
    assets_root = doc_dir / f"{doc_id}_assets"
    figures = len(list((assets_root / "figures").glob("*"))) if (assets_root / "figures").exists() else 0
    tables = len(list((assets_root / "tables").glob("*"))) if (assets_root / "tables").exists() else 0
    pages = len(list((assets_root / "page_images").glob("*"))) if (assets_root / "page_images").exists() else 0
    return {"figures": figures, "tables": tables, "page_images": pages}


def _worker_extract_doc(
    *,
    local_pdf_path: str,
    markdown_path: str,
    ocr_server: Optional[str],
    ocr_model: str,
    ocr_workspace: str,
    use_pdf_page_ocr: bool,
    result_queue: "mp.Queue[Dict[str, Any]]",
) -> None:
    try:
        from ocr_agent.hybrid_pdf_extractor import HybridPDFExtractor, PipelineCustomOCRBackend
        from ocr_agent.pipeline_custom import make_ocr_args

        backend = None
        backend_name = "dummy"
        if ocr_server:
            ocr_args = make_ocr_args(
                server=ocr_server,
                model=ocr_model,
                workspace=ocr_workspace,
                embed_page_markers=True,
                save_rendered_pages=True,
                materialize_assets=False,
                emit_figure_placeholders=True,
            )
            backend = PipelineCustomOCRBackend(ocr_args)
            backend_name = "ocr_server"

        extractor = HybridPDFExtractor(
            pdf_path=local_pdf_path,
            ocr_backend=backend,
            use_pdf_page_ocr=bool(use_pdf_page_ocr),
        )
        start = time.perf_counter()
        saved_path = extractor.save_markdown(output_path=markdown_path)
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 3)
        markdown = Path(markdown_path).read_text(encoding="utf-8")
        document_mode = "unknown"
        for line in markdown.splitlines():
            if line.startswith("<!-- document_mode:"):
                document_mode = line.replace("<!-- document_mode:", "").replace("-->", "").strip()
                break
        result_queue.put(
            {
                "status": "success",
                "markdown_path": str(Path(saved_path).resolve()),
                "ocr_backend": backend_name,
                "use_pdf_page_ocr": bool(use_pdf_page_ocr),
                "document_mode": document_mode,
                "elapsed_ms": elapsed_ms,
            }
        )
    except Exception as exc:  # pragma: no cover - exercised through benchmark runs
        result_queue.put(
            {
                "status": "error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc(limit=20),
            }
        )


def run_ocr_agent_exports(
    docs: Sequence[BenchmarkDoc],
    *,
    ocr_server: Optional[str] = None,
    ocr_model: str = "allenai/olmOCR-2-7B-1025-FP8",
    ocr_workspace: str = "./tmp_ocr",
    use_pdf_page_ocr: bool = False,
    timeout_seconds: int = 180,
    overwrite: bool = False,
) -> List[Dict[str, Any]]:
    try:
        import ocr_agent.hybrid_pdf_extractor  # noqa: F401
        import ocr_agent.pipeline_custom  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "ocr_agent dependencies are missing. Install the required OCR stack in "
            "the active Python environment before running this benchmark."
        ) from exc

    ensure_dirs()
    system_name = "ocr_agent"
    root = system_root(system_name)
    rows: List[Dict[str, Any]] = []

    for idx, doc in enumerate(docs, start=1):
        doc_dir = system_doc_dir(system_name, doc.doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        local_pdf_path = doc_dir / f"{doc.doc_id}.pdf"
        markdown_path = doc_dir / "paper.md"
        if local_pdf_path.exists() and not overwrite:
            pass
        else:
            shutil.copy2(doc.pdf_path, local_pdf_path)

        print(f"[ocr_agent] [{idx}/{len(docs)}] start {doc.doc_id}", flush=True)
        result_queue: "mp.Queue[Dict[str, Any]]" = mp.Queue()
        process = mp.get_context("spawn").Process(
            target=_worker_extract_doc,
            kwargs={
                "local_pdf_path": str(local_pdf_path),
                "markdown_path": str(markdown_path),
                "ocr_server": ocr_server,
                "ocr_model": ocr_model,
                "ocr_workspace": ocr_workspace,
                "use_pdf_page_ocr": bool(use_pdf_page_ocr),
                "result_queue": result_queue,
            },
        )
        started_at = time.perf_counter()
        process.start()
        process.join(timeout_seconds)

        worker_result: Dict[str, Any]
        if process.is_alive():
            process.terminate()
            process.join(5)
            worker_result = {
                "status": "timeout",
                "error_type": "TimeoutExpired",
                "error_message": f"ocr_agent exceeded {timeout_seconds}s for {doc.doc_id}",
                "elapsed_ms": round((time.perf_counter() - started_at) * 1000.0, 3),
                "ocr_backend": "ocr_server" if ocr_server else "dummy",
                "use_pdf_page_ocr": bool(use_pdf_page_ocr),
                "document_mode": "unknown",
            }
        elif not result_queue.empty():
            worker_result = result_queue.get()
        else:
            worker_result = {
                "status": "error",
                "error_type": "NoResultError",
                "error_message": f"ocr_agent exited without returning a result for {doc.doc_id}",
                "elapsed_ms": round((time.perf_counter() - started_at) * 1000.0, 3),
                "ocr_backend": "ocr_server" if ocr_server else "dummy",
                "use_pdf_page_ocr": bool(use_pdf_page_ocr),
                "document_mode": "unknown",
            }

        row: Dict[str, Any] = {
            "doc_id": doc.doc_id,
            "system": system_name,
            "title": doc.title,
            "pdf_path": str(doc.pdf_path),
            "local_pdf_path": str(local_pdf_path),
            "doc_dir": str(doc_dir),
            "ocr_backend": str(worker_result.get("ocr_backend") or ("ocr_server" if ocr_server else "dummy")),
            "use_pdf_page_ocr": bool(worker_result.get("use_pdf_page_ocr", bool(use_pdf_page_ocr))),
            "document_mode": str(worker_result.get("document_mode") or "unknown"),
            "asset_counts": _count_assets(doc_dir, doc.doc_id),
            "elapsed_ms": float(worker_result.get("elapsed_ms") or round((time.perf_counter() - started_at) * 1000.0, 3)),
            "status": str(worker_result.get("status") or "error"),
        }
        if worker_result.get("markdown_path"):
            row["markdown_path"] = str(worker_result["markdown_path"])
        if worker_result.get("error_type"):
            row["error_type"] = str(worker_result["error_type"])
        if worker_result.get("error_message"):
            row["error_message"] = str(worker_result["error_message"])
        if worker_result.get("traceback"):
            row["traceback"] = str(worker_result["traceback"])
        write_json(doc_dir / "benchmark_result.json", row)
        print(
            f"[ocr_agent] [{idx}/{len(docs)}] {doc.doc_id} -> {row['status']} "
            f"({row['elapsed_ms']:.1f} ms)",
            flush=True,
        )
        rows.append(row)

    write_jsonl(root / "run_manifest.jsonl", rows)
    write_json(RUN_DIR / "latest_ocr_agent.json", {"system": system_name, "documents": rows})
    return rows


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)
    rows = run_ocr_agent_exports(
        docs,
        ocr_server=args.ocr_server,
        ocr_model=args.ocr_model,
        ocr_workspace=args.ocr_workspace,
        use_pdf_page_ocr=bool(args.use_pdf_page_ocr),
        timeout_seconds=int(args.timeout_seconds),
        overwrite=bool(args.overwrite),
    )
    print(f"[ocr_agent] exported {len(rows)} document(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
