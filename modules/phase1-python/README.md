# IA Phase 1 Python Modules

Reusable Python modules extracted from the Instructor Assistant ingestion pipeline.

## Included modules

- `ia_phase1.parser`: resolve DOI/URL/PDF URL and extract page or block text.
- `ia_phase1.sectioning`: section detection and block-level section metadata annotation.
- `ia_phase1.chunking`: chunk generation with section-aware metadata.
- `ia_phase1.tables`: structured table extraction + table chunk conversion.
- `ia_phase1.figures`: embedded + vector figure extraction with section mapping.

## Install

```bash
cd modules/phase1-python
pip install -e .
```

## Quick example (end-to-end)

```python
import asyncio
from pathlib import Path

from ia_phase1 import (
    annotate_blocks_with_sections,
    chunk_text_blocks,
    extract_and_store_paper_figures,
    extract_and_store_paper_tables,
    extract_text_blocks,
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
    figure_manifest = extract_and_store_paper_figures(pdf_path, paper_id=1, blocks=blocks)

    print(title)
    print(section_report["strategy"], len(section_report["sections"]))
    print("chunks:", len(chunks))
    print("tables:", table_manifest["num_tables"], "figures:", figure_manifest["num_images"])


asyncio.run(run())
```

## Output directories

- Default parser download dir: `.ia_phase1_data/pdfs`
- Default table output dir: `.ia_phase1_data/tables`
- Default figure output dir: `.ia_phase1_data/figures`

Override with environment variables:

- `TABLE_OUTPUT_DIR`
- `FIGURE_OUTPUT_DIR`

## Feature-specific docs

- `features/parser/README.md`
- `features/sectioning/README.md`
- `features/chunking/README.md`
- `features/tables/README.md`
- `features/figures/README.md`

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
