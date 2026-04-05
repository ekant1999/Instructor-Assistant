from __future__ import annotations

import argparse
import importlib
import multiprocessing as mp
import re
import shutil
import sys
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


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_repo_import_root() -> None:
    repo_root = str(_REPO_ROOT)
    if sys.path and sys.path[0] == repo_root:
        return
    sys.path = [entry for entry in sys.path if entry != repo_root]
    sys.path.insert(0, repo_root)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hybrid ocr_agent extractor for benchmark documents.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument(
        "--system-name",
        choices=["ocr_agent", "improved_ocr_agent"],
        default="ocr_agent",
        help="Which OCR agent package/output namespace to benchmark.",
    )
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


_OCR_PAGE_MARKER_RE = re.compile(r"^<!-- OCR page (?P<page_num>\d+) -->\s*$")
_PAGE_MODE_MARKER_RE = re.compile(r"^<!-- page \d+ mode: (?P<mode>[^>]+) -->\s*$")
_OCR_PLACEHOLDER_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<name>page_(?P<x0>\d+)_(?P<y0>\d+)_(?P<x1>\d+)_(?P<y1>\d+)\.png)\)"
)


def _materialize_ocr_placeholder_assets(*, doc_dir: Path, doc_id: str, markdown_path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        return

    markdown = markdown_path.read_text(encoding="utf-8")
    assets_root = doc_dir / f"{doc_id}_assets"
    page_dir = assets_root / "page_images"
    figure_dir = assets_root / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    rewritten_lines: List[str] = []
    current_ocr_page: Optional[int] = None

    for line in markdown.splitlines():
        page_mode = _PAGE_MODE_MARKER_RE.match(line.strip())
        if page_mode and page_mode.group("mode").strip() != "ocr":
            current_ocr_page = None
            rewritten_lines.append(line)
            continue

        marker = _OCR_PAGE_MARKER_RE.match(line.strip())
        if marker:
            current_ocr_page = int(marker.group("page_num"))
            rewritten_lines.append(line)
            continue

        if current_ocr_page is None:
            rewritten_lines.append(line)
            continue

        page_image_path = page_dir / f"{doc_id}_page_{current_ocr_page}.png"
        if not page_image_path.exists():
            rewritten_lines.append(line)
            continue

        def _replace(match: re.Match[str]) -> str:
            x0 = int(match.group("x0"))
            y0 = int(match.group("y0"))
            x1 = int(match.group("x1"))
            y1 = int(match.group("y1"))
            out_name = f"ocr_page_{current_ocr_page}_{x0}_{y0}_{x1}_{y1}.png"
            out_path = figure_dir / out_name
            if not out_path.exists():
                with Image.open(page_image_path) as image:
                    width, height = image.size
                    left = max(0, min(min(x0, x1), width))
                    upper = max(0, min(min(y0, y1), height))
                    right = max(0, min(max(x0, x1), width))
                    lower = max(0, min(max(y0, y1), height))
                    if right > left and lower > upper:
                        image.crop((left, upper, right, lower)).save(out_path, format="PNG")
            if out_path.exists():
                return f"![{match.group('alt')}]({doc_id}_assets/figures/{out_name})"
            return match.group(0)

        rewritten_lines.append(_OCR_PLACEHOLDER_RE.sub(_replace, line))

    markdown_path.write_text("\n".join(rewritten_lines) + "\n", encoding="utf-8")


def _worker_extract_doc(
    *,
    package_name: str,
    local_pdf_path: str,
    markdown_path: str,
    ocr_server: Optional[str],
    ocr_model: str,
    ocr_workspace: str,
    use_pdf_page_ocr: bool,
    result_queue: "mp.Queue[Dict[str, Any]]",
) -> None:
    try:
        _ensure_repo_import_root()
        extractor_module = importlib.import_module(f"{package_name}.hybrid_pdf_extractor")
        ocr_module = importlib.import_module(f"{package_name}.pipeline_custom")
        HybridPDFExtractor = extractor_module.HybridPDFExtractor
        PipelineCustomOCRBackend = extractor_module.PipelineCustomOCRBackend
        make_ocr_args = ocr_module.make_ocr_args

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
        _materialize_ocr_placeholder_assets(
            doc_dir=Path(markdown_path).parent,
            doc_id=Path(markdown_path).parent.name,
            markdown_path=Path(markdown_path),
        )
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
                "extractor_module_path": str(getattr(extractor_module, "__file__", "")),
                "postprocess_enabled": bool(getattr(extractor_module, "normalize_markdown", None)),
                "ocr_backend": backend_name,
                "use_pdf_page_ocr": bool(use_pdf_page_ocr),
                "document_mode": document_mode,
                "elapsed_ms": elapsed_ms,
                "non_ocr_routing": dict(getattr(extractor, "last_routing_info", {}) or {}),
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
    system_name: str = "ocr_agent",
    package_name: str = "ocr_agent",
    ocr_server: Optional[str] = None,
    ocr_model: str = "allenai/olmOCR-2-7B-1025-FP8",
    ocr_workspace: str = "./tmp_ocr",
    use_pdf_page_ocr: bool = False,
    timeout_seconds: int = 180,
    overwrite: bool = False,
) -> List[Dict[str, Any]]:
    try:
        _ensure_repo_import_root()
        importlib.import_module(f"{package_name}.hybrid_pdf_extractor")
        importlib.import_module(f"{package_name}.pipeline_custom")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"{package_name} dependencies are missing. Install the required OCR stack in "
            "the active Python environment before running this benchmark."
        ) from exc

    ensure_dirs()
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

        print(f"[{system_name}] [{idx}/{len(docs)}] start {doc.doc_id}", flush=True)
        result_queue: "mp.Queue[Dict[str, Any]]" = mp.Queue()
        process = mp.get_context("spawn").Process(
            target=_worker_extract_doc,
            kwargs={
                "package_name": package_name,
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
                "error_message": f"{system_name} exceeded {timeout_seconds}s for {doc.doc_id}",
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
                "error_message": f"{system_name} exited without returning a result for {doc.doc_id}",
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
        if worker_result.get("extractor_module_path"):
            row["extractor_module_path"] = str(worker_result["extractor_module_path"])
        if "postprocess_enabled" in worker_result:
            row["postprocess_enabled"] = bool(worker_result["postprocess_enabled"])
        if worker_result.get("non_ocr_routing"):
            routing = dict(worker_result["non_ocr_routing"])
            row["non_ocr_document_handler"] = str(routing.get("document_handler") or "unknown")
            row["non_ocr_runs"] = list(routing.get("runs") or [])
            row["ia_score"] = routing.get("ia_score")
            row["native_score"] = routing.get("native_score")
            row["non_ocr_page_handlers"] = dict(routing.get("page_handlers") or {})
            row["non_ocr_scores"] = dict(routing.get("scores") or {})
        if worker_result.get("error_type"):
            row["error_type"] = str(worker_result["error_type"])
        if worker_result.get("error_message"):
            row["error_message"] = str(worker_result["error_message"])
        if worker_result.get("traceback"):
            row["traceback"] = str(worker_result["traceback"])
        write_json(doc_dir / "benchmark_result.json", row)
        print(
            f"[{system_name}] [{idx}/{len(docs)}] {doc.doc_id} -> {row['status']} "
            f"({row['elapsed_ms']:.1f} ms)",
            flush=True,
        )
        rows.append(row)

    write_jsonl(root / "run_manifest.jsonl", rows)
    write_json(RUN_DIR / f"latest_{system_name}.json", {"system": system_name, "documents": rows})
    return rows


def run_improved_ocr_agent_exports(
    docs: Sequence[BenchmarkDoc],
    *,
    ocr_server: Optional[str] = None,
    ocr_model: str = "allenai/olmOCR-2-7B-1025-FP8",
    ocr_workspace: str = "./tmp_ocr",
    use_pdf_page_ocr: bool = False,
    timeout_seconds: int = 180,
    overwrite: bool = False,
) -> List[Dict[str, Any]]:
    return run_ocr_agent_exports(
        docs,
        system_name="improved_ocr_agent",
        package_name="improved_ocr_agent",
        ocr_server=ocr_server,
        ocr_model=ocr_model,
        ocr_workspace=ocr_workspace,
        use_pdf_page_ocr=use_pdf_page_ocr,
        timeout_seconds=timeout_seconds,
        overwrite=overwrite,
    )


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)
    rows = run_ocr_agent_exports(
        docs,
        system_name=args.system_name,
        package_name=args.system_name,
        ocr_server=args.ocr_server,
        ocr_model=args.ocr_model,
        ocr_workspace=args.ocr_workspace,
        use_pdf_page_ocr=bool(args.use_pdf_page_ocr),
        timeout_seconds=int(args.timeout_seconds),
        overwrite=bool(args.overwrite),
    )
    print(f"[{args.system_name}] exported {len(rows)} document(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
