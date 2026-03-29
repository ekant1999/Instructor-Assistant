#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a PDF into the markdown bundle format.")
    parser.add_argument(
        "--pdf-source",
        "--pdf-path",
        dest="pdf_source",
        required=True,
        help="Local PDF path or resolvable source URL/DOI/arXiv/Drive link.",
    )
    parser.add_argument(
        "--paper-id",
        type=int,
        help="Optional paper id override used for asset/output folder naming. If omitted, a stable local id is derived from the resolved PDF content.",
    )
    parser.add_argument("--output-dir", help="Optional output directory for the markdown bundle.")
    parser.add_argument(
        "--output-root",
        help="Optional root directory for pdfs/, tables/, equations/, figures/, and markdown/ subfolders.",
    )
    parser.add_argument("--source-url", help="Optional source URL to include in frontmatter/manifest.")
    parser.add_argument("--title", help="Optional title override for frontmatter metadata.")
    parser.add_argument(
        "--asset-mode",
        choices=["copy", "reference"],
        default="copy",
        help="How bundle assets should be handled.",
    )
    parser.add_argument(
        "--asset-path-mode",
        choices=["relative", "absolute"],
        default="relative",
        help="Whether markdown should use relative or absolute asset paths.",
    )
    parser.add_argument(
        "--include-frontmatter",
        dest="include_frontmatter",
        action="store_true",
        default=True,
        help="Include YAML frontmatter in paper.md (default: enabled).",
    )
    parser.add_argument(
        "--no-frontmatter",
        dest="include_frontmatter",
        action="store_false",
        help="Disable YAML frontmatter in paper.md.",
    )
    parser.add_argument(
        "--include-page-markers",
        action="store_true",
        help="Insert HTML page markers into markdown output.",
    )
    parser.add_argument(
        "--prefer-equation-latex",
        dest="prefer_equation_latex",
        action="store_true",
        default=True,
        help="Prefer LaTeX equation blocks in markdown when available (default: enabled).",
    )
    parser.add_argument(
        "--no-prefer-equation-latex",
        dest="prefer_equation_latex",
        action="store_false",
        help="Disable LaTeX-first equation rendering.",
    )
    parser.add_argument(
        "--include-equation-fallback-assets",
        dest="include_equation_fallback_assets",
        action="store_true",
        default=True,
        help="Keep equation JSON/image fallback references in markdown (default: enabled).",
    )
    parser.add_argument(
        "--no-equation-fallback-assets",
        dest="include_equation_fallback_assets",
        action="store_false",
        help="Disable equation fallback asset references in markdown.",
    )
    parser.add_argument(
        "--ensure-assets",
        dest="ensure_assets",
        action="store_true",
        default=True,
        help="Run figure/table/equation extraction before exporting markdown (default: enabled).",
    )
    parser.add_argument(
        "--no-ensure-assets",
        dest="ensure_assets",
        action="store_false",
        help="Reuse existing extracted assets instead of regenerating them.",
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=True,
        help="Overwrite an existing bundle directory (default: enabled).",
    )
    parser.add_argument(
        "--no-overwrite",
        dest="overwrite",
        action="store_false",
        help="Fail if the output directory already exists and is not empty.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the export result as JSON instead of plain text.",
    )
    return parser


def _build_metadata(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    metadata: Dict[str, Any] = {}
    if args.title:
        metadata["title"] = args.title
    return metadata or None


def _configure_output_root(*, output_root: Path, pdf_path: Path, paper_id: int, overwrite: bool) -> Dict[str, str]:
    output_root.mkdir(parents=True, exist_ok=True)

    pdf_dir = output_root / "pdfs" / str(int(paper_id))
    table_dir = output_root / "tables"
    equation_dir = output_root / "equations"
    figure_dir = output_root / "figures"
    markdown_dir = output_root / "markdown"

    pdf_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    equation_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    copied_pdf_path = pdf_dir / pdf_path.name
    if pdf_path.resolve() != copied_pdf_path.resolve():
        if copied_pdf_path.exists() and not overwrite:
            raise FileExistsError(f"PDF copy already exists: {copied_pdf_path}")
        shutil.copy2(pdf_path, copied_pdf_path)

    os.environ["TABLE_OUTPUT_DIR"] = str(table_dir)
    os.environ["EQUATION_OUTPUT_DIR"] = str(equation_dir)
    os.environ["FIGURE_OUTPUT_DIR"] = str(figure_dir)
    os.environ["MARKDOWN_OUTPUT_DIR"] = str(markdown_dir)

    return {
        "output_root": str(output_root),
        "pdf_dir": str(pdf_dir),
        "pdf_copy_path": str(copied_pdf_path),
        "table_dir": str(table_dir),
        "equation_dir": str(equation_dir),
        "figure_dir": str(figure_dir),
        "markdown_dir": str(markdown_dir),
    }


def _resolve_pdf_source(*, pdf_source: str, output_dir: Optional[Path]) -> tuple[Path, Optional[str], Optional[str]]:
    from ia_phase1 import resolve_any_to_pdf

    candidate = Path(str(pdf_source).strip()).expanduser()
    if candidate.exists():
        return candidate.resolve(), None, None
    title, resolved = asyncio.run(resolve_any_to_pdf(pdf_source, output_dir=output_dir))
    return resolved.resolve(), title, str(pdf_source).strip()


def _derive_paper_id(*, pdf_path: Path, paper_id: Optional[int]) -> int:
    if paper_id is not None:
        return int(paper_id)
    hasher = hashlib.blake2b(digest_size=8)
    with pdf_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    raw = int.from_bytes(hasher.digest(), "big")
    return 100_000_000_000 + (raw % 900_000_000_000)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.output_dir and args.output_root:
        parser.error("--output-dir and --output-root cannot be used together")

    output_layout: Dict[str, str] = {}
    resolved_output_dir: Optional[Path] = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    output_root: Optional[Path] = Path(args.output_root).expanduser().resolve() if args.output_root else None
    download_dir: Optional[Path] = None
    if output_root and args.paper_id is not None:
        download_dir = output_root / "pdfs" / str(int(args.paper_id))
        download_dir.mkdir(parents=True, exist_ok=True)
    pdf_path, resolved_title, resolved_source_url = _resolve_pdf_source(
        pdf_source=args.pdf_source,
        output_dir=download_dir,
    )
    effective_paper_id = _derive_paper_id(pdf_path=pdf_path, paper_id=args.paper_id)
    if output_root:
        output_layout = _configure_output_root(
            output_root=output_root,
            pdf_path=pdf_path,
            paper_id=effective_paper_id,
            overwrite=bool(args.overwrite),
        )
        resolved_output_dir = None

    from backend.rag.markdown_exporter import MarkdownExportConfig, export_pdf_to_markdown

    config = MarkdownExportConfig(
        asset_mode=args.asset_mode,
        asset_path_mode=args.asset_path_mode,
        include_frontmatter=bool(args.include_frontmatter),
        include_page_markers=bool(args.include_page_markers),
        prefer_equation_latex=bool(args.prefer_equation_latex),
        include_equation_fallback_assets=bool(args.include_equation_fallback_assets),
        ensure_assets=bool(args.ensure_assets),
        overwrite=bool(args.overwrite),
    )

    result = export_pdf_to_markdown(
        pdf_path,
        paper_id=effective_paper_id,
        output_dir=resolved_output_dir,
        source_url=args.source_url or resolved_source_url,
        metadata=_build_metadata(args) or ({"title": resolved_title} if resolved_title else None),
        config=config,
    )

    payload = {
        "paper_id": int(result.paper_id),
        "paper_id_origin": "provided" if args.paper_id is not None else "derived",
        "bundle_dir": str(result.bundle_dir),
        "markdown_path": str(result.markdown_path),
        "manifest_path": str(result.manifest_path),
        "asset_counts": dict(result.asset_counts),
        "section_count": int(result.section_count),
    }
    payload.update(output_layout)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if output_layout:
            print(f"output_root: {payload['output_root']}")
            print(f"pdf_copy_path: {payload['pdf_copy_path']}")
        print(f"bundle_dir: {payload['bundle_dir']}")
        print(f"markdown_path: {payload['markdown_path']}")
        print(f"manifest_path: {payload['manifest_path']}")
        print(f"asset_counts: {json.dumps(payload['asset_counts'], ensure_ascii=False)}")
        print(f"section_count: {payload['section_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
