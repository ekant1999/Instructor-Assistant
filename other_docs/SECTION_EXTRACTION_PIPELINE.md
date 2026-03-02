# Section Extraction Pipeline

This document explains how section extraction works for PDF ingestion, including fallback behavior, strategy selection, and debugging.

## Overview

The section pipeline runs during PDF ingestion and annotates each extracted text block with section metadata (e.g., `abstract`, `introduction`, `references`).

High-level flow:

1. Extract PDF text blocks with layout metadata.
2. Build section heading candidates from multiple sources.
3. Align headings to actual PDF blocks.
4. Build section spans and annotate blocks.
5. Chunk annotated blocks and preserve section metadata in chunk metadata.

## Where It Runs

- Entry point: `backend/rag/ingest_pgvector.py` in `ingest_single_paper(...)`
- Called function: `annotate_blocks_with_sections(...)`
- Section/chunk metadata later used by:
  - search/rag context
  - ingestion info UI endpoints
  - section detail UI endpoint
  - figure-to-section mapping

## Step 1: Block Extraction

Function: `extract_text_blocks(...)` in `backend/core/pdf.py`

Each block includes:

- `page_no`
- `block_index` (order on page)
- `text`
- `bbox` (`x0`, `y0`, `x1`, `y1`)
- typography metadata (`first_line`, `line_count`, `char_count`, font-size stats, `bold_ratio`, `font_names`)

This typography metadata is important for heuristic heading detection.

## Step 2: Heading Candidate Sources

Implementation file: `backend/rag/section_extractor.py`

The system can generate heading candidates from four sources:

1. `pdf_toc`
2. `arxiv_source`
3. `grobid`
4. `heuristic`

### 2.1 PDF TOC Source (`pdf_toc`)

Function: `_extract_headings_from_pdf_toc(...)`

- Reads document outline via `doc.get_toc()`
- Keeps clean/valid titles
- Uses `page_hint` from TOC entries
- High base confidence (`0.97` for level-1 headings)

### 2.2 arXiv Source Parsing (`arxiv_source`)

Functions:

- `_extract_headings_from_arxiv_source(...)`
- `_parse_latex_headings(...)`

Behavior:

- Detect arXiv ID from `source_url`
- Download source tarball from `https://arxiv.org/e-print/<id>`
- Parse `.tex` files, pick main TeX, extract:
  - abstract
  - `\section{...}` (and optional subsections)
  - references markers

### 2.3 GROBID TEI (`grobid`)

Function: `_extract_headings_with_grobid(...)`

Behavior:

- Sends PDF to GROBID endpoint `/api/processFulltextDocument`
- Parses TEI XML
- Extracts abstract and `<div><head>` section headings
- Optional subsection inclusion

### 2.4 Heuristic Extraction (`heuristic`)

Function: `_extract_heuristic_headings(...)`

Signals used:

- numeric headings (`1 Introduction`, `2.1 Method`)
- Roman headings (`I. INTRODUCTION`)
- ALL CAPS heading lines
- title-case + font prominence + bold ratio
- guardrails to exclude noise (Figure/Table/Lemma/etc.)

## Step 3: Heading Alignment to Blocks

Function: `_align_headings_to_spans(...)`

How alignment works:

- Normalizes heading text and early block text
- Computes a match score (`substring`, token overlap, sequence similarity)
- Uses `page_hint` to constrain scan window when available
- Applies source-specific thresholds:
  - `pdf_toc`: `0.38`
  - `arxiv_source`: `0.55`
  - `grobid`: `0.58`
  - `heuristic`: `0.42`

If score is low but `page_hint` exists, a page-position fallback may still place heading start.

## Step 4: Span Construction and Fallbacks

After aligned heading starts are found:

- Consecutive starts define `[start_idx, end_idx]` spans.
- Content before first heading becomes `front_matter` (`source = fallback`, low confidence).
- If no spans at all, entire document becomes one fallback section:
  - `title = Document Body`
  - `canonical = other`
  - `source = fallback`

Block metadata written per block:

- `section_title`
- `section_canonical`
- `section_level`
- `section_source`
- `section_confidence`
- `section_index`

## Step 5: Strategy Selection Logic

Function: `annotate_blocks_with_sections(...)`

Important runtime behavior:

1. Build heuristic headings first.
2. Build TOC headings and optionally inject heuristic `Abstract`/`References` into TOC if missing.
3. If TOC produces at least 3 non-front-matter spans, choose `pdf_toc` immediately.
4. Otherwise, score available sources (`pdf_toc`, `arxiv_source`, `grobid`, `heuristic`) and choose highest.

Scoring factors:

- number of matched non-front spans
- coverage ratio (`matched / candidate headings`)
- average section confidence
- source bonus:
  - `pdf_toc = 1.25`
  - `arxiv_source = 1.10`
  - `grobid = 1.00`
  - `heuristic = 0.70`

## Canonical Section Mapping

Function: `canonicalize_heading(...)`

Known headings map to canonical labels via pattern table (examples):

- `abstract`
- `introduction`
- `related_work`
- `methodology`
- `experiments`
- `results`
- `conclusion`
- `references`

Unknown headings are slugified into stable canonical keys (e.g., `problem_formulation`).

## Chunk-Level Metadata Propagation

File: `backend/rag/chunking.py`

Chunk metadata is built from the annotated source blocks and includes:

- `section_primary`
- `section_all`
- `section_titles`
- `section_source`
- `section_source_all`
- `section_confidence`
- original `blocks` list

So a chunk can represent one or multiple sections while preserving provenance.

## APIs Used for Inspection

These endpoints help inspect extraction quality:

- `GET /api/papers/{paper_id}/ingestion-info`
  - section buckets
  - chunks
  - chunk metadata
- `GET /api/papers/{paper_id}/ingestion-sections/{section_canonical}`
  - reconstructed full section text
  - section pages
  - related extracted images

## Environment Variables

Section extraction:

- `ARXIV_SOURCE_TIMEOUT` (default `20`)
- `ARXIV_INCLUDE_SUBSECTIONS` (`0/1`, default `0`)
- `GROBID_URL` (empty => GROBID disabled)
- `GROBID_TIMEOUT` (default `45`)
- `GROBID_INCLUDE_SUBSECTIONS` (`0/1`, default `0`)

Figure extraction (downstream mapping quality):

- `FIGURE_OUTPUT_DIR`
- `FIGURE_MIN_PIXEL_AREA`
- `FIGURE_MIN_SIDE_PX`
- `FIGURE_MIN_RENDER_SIDE_PT`
- `FIGURE_MIN_RENDER_AREA`

## Why Fallback Happens

Common reasons:

- No/weak PDF TOC
- arXiv source unavailable for that URL
- GROBID not configured or unreachable
- non-standard heading styles in the paper
- scanned/low-quality PDFs with weak text extraction

## Troubleshooting Checklist

1. Verify strategy in ingestion info (`pdf_toc`, `arxiv_source`, `grobid`, `heuristic`, `fallback`).
2. Check if `source_url` is a real arXiv URL for arXiv parsing.
3. If using GROBID, verify `GROBID_URL` and health endpoint.
4. Re-ingest paper after changing env/settings.
5. Use ingestion info dialog to inspect:
   - section ordering
   - chunk metadata (`section_all`, `section_primary`)
   - section detail text

## Notes

- `front_matter` is expected for content before first detected section heading.
- The top-of-file comment in `section_extractor.py` mentions a fallback chain, but runtime currently gives strong preference to `pdf_toc` when TOC coverage is good.
