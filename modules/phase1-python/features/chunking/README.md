# Chunking Module

File: `src/ia_phase1/chunking.py`

## What it does

Converts section-annotated text blocks into embedding-ready chunks while preserving metadata.

## API

- `chunk_text_blocks(blocks, target_size=1000, overlap=200, min_chunk_size=100)`
- `simple_chunk_blocks(blocks, max_chars=1200)`

## Metadata added to each chunk

- `chunk_type`
- `section_primary`
- `section_all`
- `section_titles`
- `section_source`
- `section_confidence`
- `spans_multiple_sections`
- `blocks` (source block snapshots)

## Usage

```python
from ia_phase1.chunking import chunk_text_blocks

chunks = chunk_text_blocks(blocks, target_size=900, overlap=150)
print(len(chunks), chunks[0]["metadata"]["section_primary"])
```

## Dependencies

Standard library only.
