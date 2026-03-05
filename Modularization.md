# Modularization

This project currently exposes reusable ingestion + search/retrieval features as a Python package:

- Package root: `modules/phase1-python`
- Import path after install: `ia_phase1`

## Modularized Features

1. `parser`
- What: DOI/URL/arXiv/direct-PDF resolution, PDF text extraction.
- Module: `modules/phase1-python/src/ia_phase1/parser.py`
- Docs: `modules/phase1-python/features/parser/README.md`

2. `sectioning`
- What: research-paper section detection + canonical section mapping.
- Module: `modules/phase1-python/src/ia_phase1/sectioning.py`
- Docs: `modules/phase1-python/features/sectioning/README.md`

3. `chunking`
- What: section-aware chunk generation from extracted blocks.
- Module: `modules/phase1-python/src/ia_phase1/chunking.py`
- Docs: `modules/phase1-python/features/chunking/README.md`

4. `tables`
- What: structured table extraction + table chunk conversion.
- Module: `modules/phase1-python/src/ia_phase1/tables.py`
- Docs: `modules/phase1-python/features/tables/README.md`

5. `figures`
- What: embedded image extraction + vector figure rendering with section mapping.
- Module: `modules/phase1-python/src/ia_phase1/figures.py`
- Docs: `modules/phase1-python/features/figures/README.md`

6. `youtube_transcript`
- What: YouTube subtitle extraction (`yt-dlp`) + cleaned transcript text generation.
- Module: `modules/phase1-python/src/ia_phase1/youtube_transcript.py`
- Docs: `modules/phase1-python/features/youtube-transcript/README.md`

7. `equations`
- What: display-equation extraction + equation image crops + equation chunk conversion.
- Module: `modules/phase1-python/src/ia_phase1/equations.py`
- Docs: `modules/phase1-python/features/equations/README.md`

8. `search` (keyword + hybrid + context helpers)
- What: SQLite keyword search, pgvector/PostgreSQL hybrid fusion, and section-hit snippet localization.
- Modules:
  - `modules/phase1-python/src/ia_phase1/search_keyword.py`
  - `modules/phase1-python/src/ia_phase1/search_hybrid.py`
  - `modules/phase1-python/src/ia_phase1/search_context.py`
- Docs: `modules/phase1-python/features/search/README.md`

## Install

```bash
cd modules/phase1-python
pip install -e .
```

## Minimal Usage

```python
from ia_phase1 import resolve_any_to_pdf, annotate_blocks_with_sections, chunk_text_blocks
```

## Optional Feature Dependency Installs

```bash
cd modules/phase1-python

# all core deps used by phase1 package
pip install -r requirements.txt

# tests
pip install -r requirements-test.txt
```

## Existing Backend Integration

The backend already consumes these modules (for example YouTube transcript flow) via compatibility wrappers, so app behavior stays the same while logic remains reusable.
