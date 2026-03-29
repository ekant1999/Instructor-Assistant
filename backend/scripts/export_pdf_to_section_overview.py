#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import argparse
import hashlib
import json
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
    parser = argparse.ArgumentParser(description="Export a PDF section overview as JSON and markdown.")
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
        help="Optional paper id override used for output folder naming. If omitted, a stable local id is derived from the resolved PDF content.",
    )
    parser.add_argument("--output-dir", help="Optional directory to write section_overview.json and section_overview.md.")
    parser.add_argument(
        "--output-root",
        help="Optional root directory for pdfs/ and section_overview/ subfolders.",
    )
    parser.add_argument("--source-url", help="Optional source URL to attach to overview metadata.")
    parser.add_argument("--title", help="Optional title override.")
    parser.add_argument(
        "--include-front-matter",
        dest="include_front_matter",
        action="store_true",
        default=False,
        help="Include front matter in the section overview.",
    )
    parser.add_argument(
        "--include-references",
        action="store_true",
        help="Include references in the section overview.",
    )
    parser.add_argument(
        "--include-acknowledgements",
        action="store_true",
        help="Include acknowledgements in the section overview.",
    )
    parser.add_argument(
        "--include-appendix",
        action="store_true",
        help="Include appendix sections in the section overview.",
    )
    parser.add_argument(
        "--min-sentences-per-section",
        type=int,
        default=1,
        help="Minimum number of sentences per section summary.",
    )
    parser.add_argument(
        "--max-sentences-per-section",
        type=int,
        default=4,
        help="Maximum number of sentences per section summary.",
    )
    parser.add_argument(
        "--min-words-per-section",
        type=int,
        default=75,
        help="Minimum target word budget per section summary.",
    )
    parser.add_argument(
        "--max-words-per-section",
        type=int,
        default=220,
        help="Maximum target word budget per section summary.",
    )
    parser.add_argument(
        "--sentence-similarity-threshold",
        type=float,
        default=0.72,
        help="Maximum Jaccard similarity allowed between selected sentences.",
    )
    parser.add_argument(
        "--max-sentence-chars",
        type=int,
        default=360,
        help="Maximum sentence length used in section summarization.",
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=True,
        help="Overwrite existing output files (default: enabled).",
    )
    parser.add_argument(
        "--no-overwrite",
        dest="overwrite",
        action="store_false",
        help="Fail if output files already exist.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result payload as JSON instead of plain text.",
    )
    return parser


def _derive_paper_id(*, pdf_path: Path, paper_id: Optional[int]) -> int:
    if paper_id is not None:
        return int(paper_id)
    hasher = hashlib.blake2b(digest_size=8)
    with pdf_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    raw = int.from_bytes(hasher.digest(), "big")
    return 100_000_000_000 + (raw % 900_000_000_000)


def _output_dir_from_args(
    args: argparse.Namespace,
    pdf_path: Path,
    paper_id: int,
) -> tuple[Optional[Path], Dict[str, str]]:
    if args.output_dir and args.output_root:
        raise ValueError("--output-dir and --output-root cannot be used together")

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir, {}

    if args.output_root:
        output_root = Path(args.output_root).expanduser().resolve()
        key = str(int(paper_id))
        pdf_dir = output_root / "pdfs" / key
        overview_dir = output_root / "section_overview" / key
        pdf_dir.mkdir(parents=True, exist_ok=True)
        overview_dir.mkdir(parents=True, exist_ok=True)

        copied_pdf_path = pdf_dir / pdf_path.name
        if pdf_path.resolve() != copied_pdf_path.resolve():
            if copied_pdf_path.exists() and not args.overwrite:
                raise FileExistsError(f"PDF copy already exists: {copied_pdf_path}")
            shutil.copy2(pdf_path, copied_pdf_path)

        return overview_dir, {
            "output_root": str(output_root),
            "pdf_copy_path": str(copied_pdf_path),
            "pdf_dir": str(pdf_dir),
            "overview_root": str(output_root / "section_overview"),
        }

    return None, {}


def _resolve_pdf_source(*, pdf_source: str, output_dir: Optional[Path]) -> tuple[Path, Optional[str], Optional[str]]:
    from ia_phase1 import resolve_any_to_pdf

    candidate = Path(str(pdf_source).strip()).expanduser()
    if candidate.exists():
        return candidate.resolve(), None, None
    title, resolved = asyncio.run(resolve_any_to_pdf(pdf_source, output_dir=output_dir))
    return resolved.resolve(), title, str(pdf_source).strip()


def _write_outputs(
    *,
    output_dir: Path,
    payload: Dict[str, Any],
    markdown: str,
    overwrite: bool,
) -> Dict[str, str]:
    json_path = output_dir / "section_overview.json"
    markdown_path = output_dir / "section_overview.md"
    if not overwrite:
        for candidate in (json_path, markdown_path):
            if candidate.exists():
                raise FileExistsError(f"Output already exists: {candidate}")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return {
        "output_dir": str(output_dir),
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    from ia_phase1.section_overview import (
        SectionOverviewConfig,
        build_section_overview,
        render_section_overview_markdown,
    )

    config = SectionOverviewConfig(
        include_front_matter=bool(args.include_front_matter),
        include_references=bool(args.include_references),
        include_acknowledgements=bool(args.include_acknowledgements),
        include_appendix=bool(args.include_appendix),
        min_sentences_per_section=int(args.min_sentences_per_section),
        max_sentences_per_section=int(args.max_sentences_per_section),
        min_words_per_section=int(args.min_words_per_section),
        max_words_per_section=int(args.max_words_per_section),
        sentence_similarity_threshold=float(args.sentence_similarity_threshold),
        max_sentence_chars=int(args.max_sentence_chars),
    )
    download_dir: Optional[Path] = None
    if args.output_root and args.paper_id is not None:
        key = str(int(args.paper_id))
        download_dir = Path(args.output_root).expanduser().resolve() / "pdfs" / key
        download_dir.mkdir(parents=True, exist_ok=True)
    pdf_path, resolved_title, resolved_source_url = _resolve_pdf_source(
        pdf_source=args.pdf_source,
        output_dir=download_dir,
    )
    effective_paper_id = _derive_paper_id(pdf_path=pdf_path, paper_id=args.paper_id)
    metadata = {"title": args.title} if args.title else ({"title": resolved_title} if resolved_title else None)
    output_dir, extra_paths = _output_dir_from_args(args, pdf_path, effective_paper_id)

    result = build_section_overview(
        pdf_path,
        source_url=args.source_url or resolved_source_url,
        metadata=metadata,
        config=config,
    )
    markdown = render_section_overview_markdown(result)
    payload = result.to_dict()
    payload["paper_id"] = int(effective_paper_id)
    payload["paper_id_origin"] = "provided" if args.paper_id is not None else "derived"

    file_paths: Dict[str, str] = {}
    if output_dir is not None:
        file_paths = _write_outputs(
            output_dir=output_dir,
            payload=payload,
            markdown=markdown,
            overwrite=bool(args.overwrite),
        )

    response = {
        "paper_id": int(effective_paper_id),
        "paper_id_origin": "provided" if args.paper_id is not None else "derived",
        "title": result.title,
        "source_pdf": str(result.source_pdf),
        "section_count": int(result.section_count),
        "sections": [
            {
                "section_title": item.section_title,
                "section_canonical": item.section_canonical,
                "page_start": int(item.page_start),
                "page_end": int(item.page_end),
                "summary_paragraph": item.summary_paragraph,
            }
            for item in result.sections
        ],
    }
    response.update(extra_paths)
    response.update(file_paths)

    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        if extra_paths.get("output_root"):
            print(f"output_root: {extra_paths['output_root']}")
            print(f"pdf_copy_path: {extra_paths['pdf_copy_path']}")
        if file_paths.get("output_dir"):
            print(f"output_dir: {file_paths['output_dir']}")
            print(f"json_path: {file_paths['json_path']}")
            print(f"markdown_path: {file_paths['markdown_path']}")
        print(f"title: {response['title']}")
        print(f"source_pdf: {response['source_pdf']}")
        print(f"section_count: {response['section_count']}")
        for section in response["sections"]:
            print(f"- {section['section_title']} [{section['page_start']}-{section['page_end']}]")
            print(f"  {section['summary_paragraph']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
