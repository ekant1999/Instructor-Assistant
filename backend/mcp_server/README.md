# MCP Server

`backend/mcp_server/app.py` runs the local MCP server for LLM tool access.

It currently exposes three groups of tools:

- context tools
- question-set tools
- library retrieval tools

## Run

From the repo root:

```bash
source backend/.webenv/bin/activate
python -m backend.mcp_server.app
```

The server runs over streamable HTTP at:

- `/mcp`

If you want other backend components to call it, set in `backend/.env`:

```env
LOCAL_MCP_SERVER_URL=http://127.0.0.1:8020/mcp
```

## Mock Flow Testing

If you want to test the library MCP tools without using a real LLM, use:

```bash
backend/.webenv/bin/python backend/scripts/mock_library_mcp_flows.py --mode direct --paper-query "WorldCam"
```

This simulates a sequence of LLM-style requests:

1. find a paper
2. get the PDF reference
3. get an excerpt
4. list sections
5. get a section
6. list figures
7. get a figure
8. load the paper into the MCP context store
9. list contexts
10. read context text

Two logs are written per run:

- human-readable log:
  - `backend/logs/mcp_mock/*.log`
- structured event log:
  - `backend/logs/mcp_mock/*.jsonl`

If you want to test the real MCP transport instead of direct function calls:

1. start the MCP server
2. ensure `LOCAL_MCP_SERVER_URL` is configured
3. run:

```bash
backend/.webenv/bin/python backend/scripts/mock_library_mcp_flows.py --mode mcp --paper-query "WorldCam"
```

## Context Tools

These manage text contexts that LLMs can read incrementally.

- `upload_context`
- `list_contexts`
- `read_context`
- `delete_context`

These are already used by the question-set flow and are also useful for library paper loading.

## Question-Set Tools

- `generate_question_set`
- `extract_questions_and_answers` (currently unsupported placeholder)
- `list_question_sets`
- `get_question_set`
- `save_question_set`
- `update_question_set`
- `delete_question_set`

## Library Retrieval Tools

These tools let an LLM work against the research library without manually handling raw PDF files.

### Paper Lookup

- `find_library_paper`

Inputs:

- `query`
- optional `limit`
- optional `search_type`

Returns matching papers with:

- `paper_id`
- `title`
- `source_url`
- `pdf_reference`

### PDF Access

- `get_library_pdf`

Inputs:

- `paper_id`
- optional `delivery`
  - `reference` (default)
  - `base64`

Behavior:

- `reference` returns a backend file reference
- `base64` returns the actual PDF bytes inline

For most LLM use, `reference` is preferred.

### Excerpt Access

- `get_library_excerpt`

Inputs:

- `paper_id`
- one of:
  - `query`
  - `page_no`
  - `section_id`
- optional `max_chars`
- optional `search_type`

Behavior:

- if `query` is used, it reuses the existing paper-section localization pipeline
- if `page_no` or `section_id` is used, it returns the requested text directly

### Section Access

- `list_library_sections`
- `get_library_section`

`list_library_sections` returns the available canonical ingestion sections for a paper.

`get_library_section` returns:

- section text
- pages
- section metadata
- associated figures
- associated equations
- associated tables

### Figure Access

- `list_library_figures`
- `get_library_figure`

`get_library_figure` supports:

- `reference` (default)
- `base64`

Like `get_library_pdf`, reference mode is the preferred default.

### Load Into Context Store

- `load_library_paper_context`

This is the most useful bridge for LLM workflows.

Inputs:

- `paper_id`
- optional `section_canonical`
- optional `max_chars`

Behavior:

- loads the full paper text, or one named section, into the existing MCP `context_store`
- returns a normal `context_id`
- after that, the LLM can use `read_context`

## Recommended LLM Flow

For most paper-reading tasks, use this sequence:

1. `find_library_paper`
2. `load_library_paper_context`
3. `read_context`

This is better than moving full PDF bytes through the tool channel.

For targeted retrieval:

1. `find_library_paper`
2. `get_library_excerpt`
3. optionally `get_library_section`

For figure/image retrieval:

1. `find_library_paper`
2. `list_library_figures`
3. `get_library_figure`

## Reference Payloads

File/image tools return references by default.

Typical reference payload:

```json
{
  "api_path": "/api/papers/99/file"
}
```

If `LIBRARY_TOOL_API_BASE` is set in `backend/.env`, the payload also includes:

```json
{
  "api_path": "/api/papers/99/file",
  "api_url": "http://localhost:8010/api/papers/99/file"
}
```

Set:

```env
LIBRARY_TOOL_API_BASE=http://localhost:8010
```

Use `base64` delivery only when the actual bytes are required inline.

## Current Scope

The library MCP tools currently cover:

- paper lookup
- PDF reference/inline access
- excerpt retrieval
- section retrieval
- figure retrieval
- loading papers or sections into the MCP context store

Not currently implemented:

- direct MCP retrieval of raw table/equation JSON files
- private Google Drive OAuth flows
- automatic host-side fetching of `api_url` references
