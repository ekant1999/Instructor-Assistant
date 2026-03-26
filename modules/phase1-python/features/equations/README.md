# Equations Module

File: `src/ia_phase1/equations.py`

## What it does

- Detects display equations from PDF line groups using a markdown-first / math-aware heuristic path.
- Renders equation crops to image files for faithful visual display.
- Derives equation LaTeX via a deterministic text-to-LaTeX fallback for markdown export.
- Maps each equation to a section using block geometry + section metadata.
- Stores per-paper JSON manifest and per-equation JSON artifacts.
- Converts equation records into chunk records for vector indexing.
- Normalizes common LaTeX math delimiters before equation text is stored.

## API

- `extract_and_store_paper_equations(pdf_path, paper_id, blocks) -> Dict[str, Any]`
- `load_paper_equation_manifest(paper_id) -> Dict[str, Any]`
- `equation_records_to_chunks(equations, text_blocks) -> List[Dict[str, Any]]`
- `resolve_equation_file(paper_id, file_name) -> Path`
- `extract_equation_latex(image_path, fallback_text, equation_number) -> Dict[str, Any]`

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
- `EQUATION_LINE_STRONG_MIN_SCORE`
- `EQUATION_LINE_SUPPORT_MIN_SCORE`
- `EQUATION_LINE_GROUP_VERTICAL_GAP_PT`
- `EQUATION_NUMBER_LINE_GAP_PT`
- `EQUATION_RENDER_SCALE`
- `EQUATION_CLIP_MARGIN_PT`
- `EQUATION_CHUNK_MAX_CHARS`
- `EQUATION_LATEX_ENABLED`
- `EQUATION_LATEX_BACKEND`
- `EQUATION_LATEX_TEXT_FALLBACK_ENABLED`

## Output

Default root: `.ia_phase1_data/equations/<paper_id>/`

- `manifest.json`
- `equation_0001.png`, `equation_0002.png`, ...
- `equation_0001.json`, `equation_0002.json`, ...

Each per-equation JSON now includes:

- `latex`
- `latex_confidence`
- `latex_source`
- `latex_validation_flags`
- `render_mode`

`EQUATION_LATEX_BACKEND=text` uses the fast text-to-LaTeX normalizer only. This keeps markdown export able to emit `$$...$$` blocks without any OCR dependency or model startup cost.

## Dependencies

Install from `requirements.txt` in this folder.
