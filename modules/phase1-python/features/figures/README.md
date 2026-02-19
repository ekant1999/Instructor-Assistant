# Figures Module

File: `src/ia_phase1/figures.py`

## What it does

- Extracts embedded bitmap images from PDF pages.
- Optionally extracts vector figures by rendering caption-guided drawing regions.
- Maps each figure to a section using text-block geometry.
- Stores per-paper image files + manifest.

## API

- `extract_and_store_paper_figures(pdf_path, paper_id, blocks) -> Dict[str, Any]`
- `load_paper_figure_manifest(paper_id) -> Dict[str, Any]`
- `resolve_figure_file(paper_id, file_name) -> Path`

## Usage

```python
from ia_phase1.figures import extract_and_store_paper_figures

manifest = extract_and_store_paper_figures(pdf_path, paper_id=42, blocks=blocks)
print(manifest["num_images"])
```

## Key environment variables

- `FIGURE_OUTPUT_DIR`
- `FIGURE_MIN_PIXEL_AREA`
- `FIGURE_MIN_SIDE_PX`
- `FIGURE_VECTOR_ENABLED`
- `FIGURE_VECTOR_RENDER_SCALE`
- `FIGURE_VECTOR_DEDUP_IOU`

## Output

Default root: `.ia_phase1_data/figures/<paper_id>/`

- `manifest.json`
- `page_001_img_001.png` (embedded)
- `page_001_vec_001.png` (vector render, when enabled)

## Dependencies

Install from `requirements.txt` in this folder.
