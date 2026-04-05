from __future__ import annotations

import argparse

from markdown_evaluation.scripts.bootstrap_gold_templates import bootstrap_gold_templates
from markdown_evaluation.scripts.normalize_outputs import normalize_system_outputs
from markdown_evaluation.scripts.run_ia_phase1 import run_ia_phase1_exports
from markdown_evaluation.scripts.run_ocr_agent import (
    run_improved_ocr_agent_exports,
    run_improved_ocr_agent_marker_exports,
    run_ocr_agent_exports,
)
from markdown_evaluation.scripts.score_outputs import score_outputs
from markdown_evaluation.scripts._common import select_docs


SYSTEMS = ("ia_phase1", "ocr_agent", "improved_ocr_agent", "improved_ocr_agent_marker")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the markdown extraction benchmark end-to-end.")
    parser.add_argument("--doc-ids", nargs="*", help="Optional subset of benchmark doc_ids.")
    parser.add_argument("--systems", nargs="*", default=list(SYSTEMS), choices=list(SYSTEMS))
    parser.add_argument("--skip-run", action="store_true", default=False)
    parser.add_argument("--skip-normalize", action="store_true", default=False)
    parser.add_argument("--skip-score", action="store_true", default=False)
    parser.add_argument("--bootstrap-gold", action="store_true", default=False)
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--ensure-assets", action="store_true", default=False)
    parser.add_argument("--ocr-server")
    parser.add_argument("--ocr-model", default="allenai/olmOCR-2-7B-1025-FP8")
    parser.add_argument("--ocr-workspace", default="./tmp_ocr")
    parser.add_argument("--use-pdf-page-ocr", action="store_true", default=False)
    parser.add_argument("--force-ocr", action="store_true", default=False, help="(Marker) Force OCR on all pages.")
    parser.add_argument("--use-llm", action="store_true", default=False, help="(Marker) Enable Ollama LLM enhancement.")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    docs = select_docs(args.doc_ids)

    if not args.skip_run:
        if "ia_phase1" in args.systems:
            run_ia_phase1_exports(
                docs,
                ensure_assets=bool(args.ensure_assets),
                overwrite=bool(args.overwrite),
            )
        if "ocr_agent" in args.systems:
            run_ocr_agent_exports(
                docs,
                ocr_server=args.ocr_server,
                ocr_model=args.ocr_model,
                ocr_workspace=args.ocr_workspace,
                use_pdf_page_ocr=bool(args.use_pdf_page_ocr),
                timeout_seconds=int(args.timeout_seconds),
                overwrite=bool(args.overwrite),
            )
        if "improved_ocr_agent" in args.systems:
            run_improved_ocr_agent_exports(
                docs,
                ocr_server=args.ocr_server,
                ocr_model=args.ocr_model,
                ocr_workspace=args.ocr_workspace,
                use_pdf_page_ocr=bool(args.use_pdf_page_ocr),
                timeout_seconds=int(args.timeout_seconds),
                overwrite=bool(args.overwrite),
            )
        if "improved_ocr_agent_marker" in args.systems:
            run_improved_ocr_agent_marker_exports(
                docs,
                force_ocr=bool(args.force_ocr),
                use_llm=bool(args.use_llm),
                timeout_seconds=int(args.timeout_seconds),
                overwrite=bool(args.overwrite),
            )

    if not args.skip_normalize:
        normalize_system_outputs(docs, systems=args.systems)

    if args.bootstrap_gold:
        bootstrap_gold_templates(docs, overwrite=bool(args.overwrite))

    if not args.skip_score:
        score_outputs(docs, systems=args.systems)

    print("[benchmark] complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
