# Tables Module

File: `src/ia_phase1/tables.py`

## What it does

- Extracts structured tables from PDFs.
- Applies false-positive filtering (figure-like layouts, prose-like matrices, noisy patterns).
- Maps each table to a section using block geometry.
- Stores per-paper JSON files + manifest.
- Converts table records to chunk records for vector indexing.

## API

- `extract_and_store_paper_tables(pdf_path, paper_id, blocks) -> Dict[str, Any]`
- `load_paper_table_manifest(paper_id) -> Dict[str, Any]`
- `table_records_to_chunks(tables, text_blocks) -> List[Dict[str, Any]]`

## Usage

```python
from ia_phase1.tables import extract_and_store_paper_tables, table_records_to_chunks

manifest = extract_and_store_paper_tables(pdf_path, paper_id=42, blocks=blocks)
table_chunks = table_records_to_chunks(manifest["tables"], blocks)
print(manifest["num_tables"], len(table_chunks))
```

## Key environment variables

- `TABLE_EXTRACTION_ENABLED`
- `TABLE_OUTPUT_DIR`
- `TABLE_MIN_ROWS`
- `TABLE_MIN_COLS`
- `TABLE_MIN_AREA_PT`
- `TABLE_TEXT_FALLBACK_ENABLED`
- `TABLE_DEDUP_IOU_THRESHOLD`

## Output

Default root: `.ia_phase1_data/tables/<paper_id>/`

- `manifest.json`
- `table_0001.json`, `table_0002.json`, ...

## Dependencies

Install from `requirements.txt` in this folder.
