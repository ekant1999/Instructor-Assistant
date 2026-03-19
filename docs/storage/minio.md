# MinIO Storage Integration

This project now uses MinIO as the durable object store for library paper files and selected derived paper artifacts.

MinIO does not replace the application databases.

- SQLite remains the source of truth for paper metadata, sections, and asset metadata.
- PostgreSQL + pgvector remains the source of truth for embeddings and semantic retrieval state.
- MinIO stores binary objects such as PDFs, figures, equation images, table/equation JSON artifacts, and thumbnails.

## What Was Added

### Asset Model

The backend now uses a `paper_assets` table to track object-backed paper files.

Each asset row stores:

- `paper_id`
- `role`
- `bucket`
- `object_key`
- `mime_type`
- `size_bytes`
- `sha256`
- `source_kind`
- `external_file_id`

This allows one paper to own multiple assets instead of relying only on a single local `pdf_path`.

### Primary PDF Storage

New PDF ingests now:

1. write a local compatibility copy
2. upload the paper PDF to MinIO
3. create a `paper_assets` row with `role='primary_pdf'`

This means a newly ingested paper is usually in the `minio_backed` state:

- local PDF exists
- MinIO object exists

### File Serving

`/api/papers/{paper_id}/file` can now serve the primary PDF from MinIO when needed.

If the local PDF is missing but the `primary_pdf` asset exists, the file can still be streamed successfully.

### Existing Library Migration

Existing local library PDFs can be uploaded into MinIO with:

```bash
backend/.webenv/bin/python backend/scripts/backfill_minio_assets.py
```

Useful flags:

- `--dry-run`
- `--limit`
- `--paper-id`
- `--force`

### Audit and Repair

Two operational scripts were added:

```bash
backend/.webenv/bin/python backend/scripts/audit_minio_assets.py
backend/.webenv/bin/python backend/scripts/repair_minio_assets.py
```

The audit script classifies papers as:

- `local_only`
- `minio_backed`
- `minio_only`
- `broken`

The repair script fixes recoverable issues such as:

- missing `primary_pdf` asset rows
- missing MinIO objects when a local PDF still exists
- optionally restoring a missing local PDF cache from MinIO

### MinIO-Only Reindex / RAG Ingest

The backend no longer requires the original local PDF to remain on disk.

If a paper has a valid `primary_pdf` asset in MinIO, the backend can:

- materialize a temp PDF from MinIO
- run section extraction
- run pgvector ingest
- run image indexing

This supports `minio_only` papers where the local PDF is gone.

### Google Docs / Drive Public Link Support

Public/shareable Google document links can now be ingested into the same asset model.

Supported source types:

- Google Docs
- Google Sheets
- Google Slides
- Google Drive file links

The backend resolves them to PDF, uploads the resulting file to MinIO, and stores the object as `role='primary_pdf'`.

This does not include private OAuth-based Google Drive access.

## Derived Artifacts Stored In MinIO

The MinIO integration now covers more than just the main paper PDF.

### Figures

Stored roles:

- `figure_image`
- `figure_manifest`

Figure serving falls back to MinIO if the local extracted figure file is missing.

### Equations

Stored roles:

- `equation_image`
- `equation_json`
- `equation_manifest`

The equation image endpoint falls back to MinIO if the local image file is missing.

### Tables

Stored roles:

- `table_json`
- `table_manifest`

Table manifests are loaded local-first and fall back to MinIO when the local manifest is missing.

### Thumbnails

Stored role:

- `paper_thumbnail`

The backend now exposes:

- `/api/papers/{paper_id}/thumbnail`

This serves the local thumbnail if present, otherwise falls back to MinIO.

## Current Asset Roles

The current storage roles in `paper_assets` include:

- `primary_pdf`
- `figure_image`
- `figure_manifest`
- `equation_image`
- `equation_json`
- `equation_manifest`
- `table_json`
- `table_manifest`
- `paper_thumbnail`

## Environment Variables

Relevant settings in `backend/.env`:

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_REGION=us-east-1
MINIO_BUCKET_LIBRARY=library-docs
MINIO_AUTO_CREATE_BUCKET=true
```

## Local Development

Example local MinIO startup:

```bash
docker run -d --name ia-minio \
  -p 9000:9000 -p 9001:9001 \
  -v ~/minio-data:/data \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data --console-address ":9001"
```

Console:

- `http://localhost:9001`

Health check:

```bash
curl http://localhost:9000/minio/health/live
```

## Operational Model

### Source of Truth

The intended durable storage model is:

- MinIO stores the canonical binary assets
- the databases store metadata and indexes
- local files are compatibility/cache copies when present

### Common Paper States

`local_only`

- local file exists
- MinIO asset missing

`minio_backed`

- local file exists
- MinIO asset exists

`minio_only`

- MinIO asset exists
- local file missing

`broken`

- metadata/object state is inconsistent

The backend is intended to operate correctly for both `minio_backed` and `minio_only` papers.

## Important Current Scope

This MinIO integration is complete for the current product needs:

- primary PDFs
- figures
- equations
- tables
- thumbnails
- audit/repair/backfill tooling
- MinIO-only reindex and RAG ingest
