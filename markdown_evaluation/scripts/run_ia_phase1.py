from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from markdown_evaluation.scripts._common import (
    RUN_DIR,
    BenchmarkDoc,
    derive_stable_paper_id,
    ensure_dirs,
    select_docs,
    system_doc_dir,
    system_root,
    temporary_environ,
    write_json,
    write_jsonl,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ia_phase1 markdown export for benchmark documents.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument("--ensure-assets", action="store_true", default=False, help="Regenerate figures/tables/equations before export.")
    parser.add_argument("--overwrite", action="store_true", default=False, help="Overwrite existing bundle directories.")
    parser.add_argument("--asset-mode", choices=["copy", "reference"], default="copy")
    parser.add_argument("--asset-path-mode", choices=["relative", "absolute"], default="relative")
    return parser


def run_ia_phase1_exports(
    docs: Sequence[BenchmarkDoc],
    *,
    ensure_assets: bool = False,
    overwrite: bool = False,
    asset_mode: str = "copy",
    asset_path_mode: str = "relative",
) -> List[Dict[str, Any]]:
    try:
        from backend.core.phase1_runtime import ensure_ia_phase1_on_path
    except ImportError:
        from core.phase1_runtime import ensure_ia_phase1_on_path

    ensure_ia_phase1_on_path()

    from ia_phase1 import MarkdownExportConfig, export_pdf_to_markdown

    ensure_dirs()
    system_name = "ia_phase1"
    root = system_root(system_name)
    runtime_root = root / "runtime"
    runtime_dirs = {
        "FIGURE_OUTPUT_DIR": str((runtime_root / "figures").resolve()),
        "TABLE_OUTPUT_DIR": str((runtime_root / "tables").resolve()),
        "EQUATION_OUTPUT_DIR": str((runtime_root / "equations").resolve()),
        "MARKDOWN_OUTPUT_DIR": str((runtime_root / "markdown").resolve()),
    }
    for value in runtime_dirs.values():
        Path(value).mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for idx, doc in enumerate(docs, start=1):
        bundle_dir = system_doc_dir(system_name, doc.doc_id)
        bundle_dir.parent.mkdir(parents=True, exist_ok=True)
        paper_id = int(doc.paper_id) if doc.paper_id is not None else derive_stable_paper_id(doc.pdf_path)
        config = MarkdownExportConfig(
            asset_mode=asset_mode,
            asset_path_mode=asset_path_mode,
            include_frontmatter=True,
            include_page_markers=False,
            prefer_equation_latex=True,
            include_equation_fallback_assets=True,
            ensure_assets=bool(ensure_assets),
            overwrite=bool(overwrite),
        )
        print(f"[ia_phase1] [{idx}/{len(docs)}] start {doc.doc_id}", flush=True)
        start = time.perf_counter()
        try:
            with temporary_environ(runtime_dirs):
                result = export_pdf_to_markdown(
                    doc.pdf_path,
                    paper_id=paper_id,
                    output_dir=bundle_dir,
                    source_url=doc.source_url,
                    metadata={"title": doc.title} if doc.title else None,
                    config=config,
                )
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 3)
            row = {
                "doc_id": doc.doc_id,
                "system": system_name,
                "paper_id": paper_id,
                "title": doc.title,
                "pdf_path": str(doc.pdf_path),
                "bundle_dir": str(result.bundle_dir),
                "markdown_path": str(result.markdown_path),
                "manifest_path": str(result.manifest_path),
                "asset_counts": dict(result.asset_counts),
                "metadata": dict(result.metadata),
                "render_mode": result.render_mode,
                "sectioning_strategy": result.sectioning_strategy,
                "sectioning_report": dict(result.sectioning_report),
                "audit": {
                    "conservative_recommended": bool(result.audit.conservative_recommended) if result.audit else False,
                    "issue_count": int(result.audit.issue_count) if result.audit else 0,
                    "issues": list(result.audit.issues) if result.audit else [],
                },
                "elapsed_ms": elapsed_ms,
                "status": "success",
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 3)
            row = {
                "doc_id": doc.doc_id,
                "system": system_name,
                "paper_id": paper_id,
                "title": doc.title,
                "pdf_path": str(doc.pdf_path),
                "bundle_dir": str(bundle_dir),
                "asset_counts": {},
                "metadata": {},
                "render_mode": "unknown",
                "sectioning_strategy": "unknown",
                "sectioning_report": {},
                "audit": {
                    "conservative_recommended": False,
                    "issue_count": 0,
                    "issues": [],
                },
                "elapsed_ms": elapsed_ms,
                "status": "error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        print(
            f"[ia_phase1] [{idx}/{len(docs)}] {doc.doc_id} -> {row['status']} "
            f"({row['elapsed_ms']:.1f} ms)",
            flush=True,
        )
        write_json(bundle_dir / "benchmark_result.json", row)
        rows.append(row)

    write_jsonl(root / "run_manifest.jsonl", rows)
    write_json(RUN_DIR / "latest_ia_phase1.json", {"system": system_name, "documents": rows})
    return rows


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)
    rows = run_ia_phase1_exports(
        docs,
        ensure_assets=bool(args.ensure_assets),
        overwrite=bool(args.overwrite),
        asset_mode=args.asset_mode,
        asset_path_mode=args.asset_path_mode,
    )
    print(f"[ia_phase1] exported {len(rows)} document(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
