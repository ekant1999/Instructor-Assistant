# Parser Module

File: `src/ia_phase1/parser.py`

## What it does

- Resolves DOI, landing page URL, arXiv URL, or direct PDF URL to a local PDF.
- Extracts page-level text (`extract_pages`).
- Extracts block-level text with geometry + font metadata (`extract_text_blocks`).

## API

- `resolve_any_to_pdf(input_str: str, output_dir: Optional[Path] = None) -> Tuple[str, Path]`
- `extract_pages(pdf_path: Path) -> List[Tuple[int, str]]`
- `extract_text_blocks(pdf_path: Path) -> List[Dict[str, Any]]`

## Usage

```python
import asyncio
from ia_phase1.parser import resolve_any_to_pdf, extract_text_blocks


async def run():
    title, pdf_path = await resolve_any_to_pdf("10.48550/arXiv.2501.00001")
    blocks = extract_text_blocks(pdf_path)
    print(title, len(blocks))


asyncio.run(run())
```

## Dependencies

Install from `requirements.txt` in this folder.
