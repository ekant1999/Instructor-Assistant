# Equations Module

File: `src/ia_phase1/equations.py`

## What it does

- Detects display equations from PDF text blocks using math-oriented heuristics.
- Renders equation crops to image files for faithful visual display.
- Maps each equation to a section using block geometry + section metadata.
- Stores per-paper JSON manifest and per-equation JSON artifacts.
- Converts equation records into chunk records for vector indexing.

## API

- `extract_and_store_paper_equations(pdf_path, paper_id, blocks) -> Dict[str, Any]`
- `load_paper_equation_manifest(paper_id) -> Dict[str, Any]`
- `equation_records_to_chunks(equations, text_blocks) -> List[Dict[str, Any]]`
- `resolve_equation_file(paper_id, file_name) -> Path`

## Usage

```python
from ia_phase1.equations import extract_and_store_paper_equations, equation_records_to_chunks

manifest = extract_and_store_paper_equations(pdf_path, paper_id=42, blocks=blocks)
equation_chunks = equation_records_to_chunks(manifest["equations"], blocks)
print(manifest["num_equations"], len(equation_chunks))
```

## Key environment variables

- `EQUATION_EXTRACTION_ENABLED`
- `EQUATION_OUTPUT_DIR`
- `EQUATION_DETECTION_MIN_SCORE`
- `EQUATION_RENDER_SCALE`
- `EQUATION_CLIP_MARGIN_PT`
- `EQUATION_CHUNK_MAX_CHARS`

## Output

Default root: `.ia_phase1_data/equations/<paper_id>/`

- `manifest.json`
- `equation_0001.png`, `equation_0002.png`, ...
- `equation_0001.json`, `equation_0002.json`, ...

## Dependencies

Install from `requirements.txt` in this folder.

