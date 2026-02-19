# Sectioning Module

File: `src/ia_phase1/sectioning.py`

## What it does

Annotates each PDF text block with:

- `section_title`
- `section_canonical`
- `section_level`
- `section_source`
- `section_confidence`
- `section_index`

## Strategy chain

The module evaluates multiple heading sources and picks the best scoring strategy:

1. PDF TOC (`pdf_toc`)
2. arXiv source headings (`arxiv_source`)
3. GROBID TEI headings (`grobid`) when `GROBID_URL` is set
4. Heuristic heading detection (`heuristic`)
5. Fallback section (`front_matter`/`other`) if needed

## API

- `annotate_blocks_with_sections(blocks, pdf_path, source_url=None) -> Dict[str, Any]`
- `canonicalize_heading(raw_title: str) -> str`

## Usage

```python
from pathlib import Path
from ia_phase1.sectioning import annotate_blocks_with_sections

report = annotate_blocks_with_sections(
    blocks=blocks,
    pdf_path=Path("/tmp/paper.pdf"),
    source_url="https://arxiv.org/abs/2501.00001",
)
print(report["strategy"], len(report["sections"]))
```

## Optional environment variables

- `GROBID_URL`
- `GROBID_TIMEOUT`
- `GROBID_INCLUDE_SUBSECTIONS`
- `ARXIV_SOURCE_TIMEOUT`
- `ARXIV_INCLUDE_SUBSECTIONS`

## Dependencies

Install from `requirements.txt` in this folder.
