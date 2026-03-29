# IA Phase 1 Python Modules

Reusable Python modules extracted from the Instructor Assistant ingestion pipeline.

## Included modules

- `ia_phase1.parser`: resolve DOI/URL/PDF URL/public Google Docs or Drive links and extract page or block text.
- `ia_phase1.sectioning`: section detection and block-level section metadata annotation.
- `ia_phase1.section_overview`: section-wise overview generation with one moderately detailed paragraph per section.
- `ia_phase1.chunking`: chunk generation with section-aware metadata.
- `ia_phase1.tables`: structured table extraction + table chunk conversion.
- `ia_phase1.figures`: embedded + vector figure extraction with section mapping.
- `ia_phase1.equations`: display-equation extraction + equation chunk conversion.
- `ia_phase1.markdown_export`: structured PDF-to-Markdown bundle export with figure/table/equation asset references.
- `ia_phase1.youtube_transcript`: YouTube subtitle extraction + cleaned transcript text generation.
- `ia_phase1.search_keyword`: keyword search utilities for SQLite-backed library data.
- `ia_phase1.search_hybrid`: pgvector + PostgreSQL FTS hybrid retrieval helpers.
- `ia_phase1.search_context`: section match localization/snippet helpers.
- `ia_phase1.search_pipeline`: unified search scoring, gating, merging, title rescue, section-to-paper aggregation, and post-ranking intra-paper localization helpers.

## Install

```bash
cd modules/phase1-python
pip install -e .
```

For search/hybrid features specifically:

```bash
cd modules/phase1-python
pip install -e .[search]
```

## Quick example (end-to-end)

```python
import asyncio
from pathlib import Path

from ia_phase1 import (
    SectionOverviewConfig,
    MarkdownExportConfig,
    annotate_blocks_with_sections,
    build_section_overview,
    chunk_text_blocks,
    extract_and_store_paper_equations,
    extract_and_store_paper_figures,
    extract_and_store_paper_tables,
    extract_text_blocks,
    export_pdf_to_markdown,
    resolve_any_to_pdf,
)


async def run() -> None:
    title, pdf_path = await resolve_any_to_pdf("https://arxiv.org/abs/2501.00001")
    blocks = extract_text_blocks(pdf_path)

    section_report = annotate_blocks_with_sections(
        blocks=blocks,
        pdf_path=Path(pdf_path),
        source_url="https://arxiv.org/abs/2501.00001",
    )

    chunks = chunk_text_blocks(blocks, target_size=1000, overlap=200)
    table_manifest = extract_and_store_paper_tables(pdf_path, paper_id=1, blocks=blocks)
    equation_manifest = extract_and_store_paper_equations(pdf_path, paper_id=1, blocks=blocks)
    figure_manifest = extract_and_store_paper_figures(pdf_path, paper_id=1, blocks=blocks)
    markdown_bundle = export_pdf_to_markdown(
        pdf_path,
        paper_id=1,
        source_url="https://arxiv.org/abs/2501.00001",
        config=MarkdownExportConfig(),
    )
    section_overview = build_section_overview(
        pdf_path,
        blocks=blocks,
        source_url="https://arxiv.org/abs/2501.00001",
        config=SectionOverviewConfig(),
    )

    print(title)
    print(section_report["strategy"], len(section_report["sections"]))
    print("chunks:", len(chunks))
    print(
        "tables:",
        table_manifest["num_tables"],
        "equations:",
        equation_manifest["num_equations"],
        "figures:",
        figure_manifest["num_images"],
    )
    print("markdown:", markdown_bundle.markdown_path)
    print("overview sections:", section_overview.section_count)


asyncio.run(run())
```

Markdown export also has a CLI wrapper:

```bash
backend/.webenv/bin/python backend/scripts/export_pdf_to_markdown.py \
  --pdf-source path/to/paper.pdf
```

`--pdf-source` can be:

- a local PDF path
- a raw PDF URL like `https://arxiv.org/pdf/1706.03762.pdf`
- an arXiv abstract URL like `https://arxiv.org/abs/1706.03762`
- a DOI like `10.48550/arXiv.1706.03762`

`--paper-id` is optional on both CLIs. If omitted, a stable local id is derived from the resolved PDF content and used for output folder naming.

To emit `pdfs/`, `tables/`, `equations/`, `figures/`, and `markdown/` under one root:

```bash
backend/.webenv/bin/python backend/scripts/export_pdf_to_markdown.py \
  --pdf-source https://arxiv.org/abs/1706.03762 \
  --output-root /tmp/paper_export
```

Using a DOI source works the same way:

```bash
backend/.webenv/bin/python backend/scripts/export_pdf_to_markdown.py \
  --pdf-source 10.48550/arXiv.1706.03762 \
  --output-root /tmp/paper_export
```

Section overview also has a CLI wrapper:

```bash
backend/.webenv/bin/python backend/scripts/export_pdf_to_section_overview.py \
  --pdf-source path/to/paper.pdf \
  --output-dir /tmp/section_overview_42
```

It accepts the same source forms, including:

- `https://arxiv.org/pdf/1706.03762.pdf`
- `https://arxiv.org/abs/1706.03762`
- `10.48550/arXiv.1706.03762`

## Output directories

- Default parser download dir: `.ia_phase1_data/pdfs`
- Default table output dir: `.ia_phase1_data/tables`
- Default equation output dir: `.ia_phase1_data/equations`
- Default figure output dir: `.ia_phase1_data/figures`
- Default markdown bundle output dir: `.ia_phase1_data/markdown`
- Default section overview output dir: `.ia_phase1_data/section_overview`

Override with environment variables:

- `TABLE_OUTPUT_DIR`
- `EQUATION_OUTPUT_DIR`
- `FIGURE_OUTPUT_DIR`
- `MARKDOWN_OUTPUT_DIR`

## Feature-specific docs

- `features/parser/README.md`
- `features/sectioning/README.md`
- `features/section_overview/README.md`
- `features/chunking/README.md`
- `features/tables/README.md`
- `features/figures/README.md`
- `features/equations/README.md`
- `features/markdown_export/README.md`
- `features/youtube-transcript/README.md`
- `features/search/README.md`

## Search example

A runnable example for the modular search pipeline lives at:

- `examples/example_search_pipeline.py`

Run it:

```bash
cd modules/phase1-python
python examples/example_search_pipeline.py
python examples/example_search_pipeline.py "vision benchmark"
```

## Testing

```bash
cd modules/phase1-python
pip install -r requirements-test.txt

# fast tests
pytest -m "not integration"

# integration contract test
pytest -m integration
```

See `tests/README.md` for details.
