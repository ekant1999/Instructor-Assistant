# Instructor Assistant

A full-stack web application for managing research papers, generating summaries, building question sets, and querying documents with hybrid search and RAG (Retrieval-Augmented Generation).

## 🎯 Features

### 📚 Research Library
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/42174f6e-ee1a-464e-b289-8d25edf2f275" />

- **Unified Hybrid Search**: Rank papers from section-level keyword + semantic hits with no-match gating and title rescue
- **Hit Navigation**: Step through all search hits inside the selected paper with previous/next controls
- **PDF Highlighting**: Phrase-first highlighting with bbox fallback for matched sections in the preview pane
- **Batch Operations**: Select multiple papers to summarize or delete at once
- **Multiple Summaries**: Generate and manage multiple summaries per paper with history
- **Advanced Editor**: Markdown editor with Edit/Preview/Split modes and auto-save
- **Exports**: Export summaries in PDF, TXT, LaTeX, Markdown, and DOCX formats
- **Save to Notes**: Save summaries to the notes library on demand

### 📝 Notes Section
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/a6af7e3f-affd-4c89-ba74-0acf01d92b9b" />

- **Unified Library**: Centralized document management for all content types
- **Smart Filtering**: Filter by document type, tags, and search across content
- **Source Tracking**: Jump back to source papers and linked documents
- **Metadata Display**: Word counts, timestamps, and generation agents

### ❓ Question Set Generation
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/4f2f8e16-2cd7-45ef-8686-7fe28afe59d3" />

- **Flexible Inputs**: Use Papers, Notes, or upload PDFs/PPT/PPTX files
- **Custom Configuration**: Configure question types, counts, and explanations
- **Incremental Generation**: Add more questions without regenerating the set
- **Question Editor**: Edit, reorder, and delete individual questions
- **Exports**: Export to Canvas, Moodle, JSON, PDF, TXT, and Markdown
- **Answer Keys**: Generate separate answer keys when exporting

### 🔍 RAG (Retrieval-Augmented Generation)
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/365b8a15-0812-412c-b545-8ef382d3322c" />

- **Multiple Agents**: GPT Web, Gemini Web, and Qwen Local
- **Selective Ingestion**: Choose which papers to index into PostgreSQL/pgvector
- **Context Templates**: Save and reuse ingestion presets
- **Query History**: Past queries with favorites and search
- **Citations**: Context-backed answers with sources

### 💬 Chat Interface
- **AI-Powered Conversations**: General assistant for research tasks
- **Attachments**: Upload PDF/PPT/PPTX in chat and ask questions against them

## 🛠️ Tech Stack

### Frontend
- **React 19** + **TypeScript**
- **Vite** for dev/build
- **Wouter** for routing
- **TanStack Query** for data fetching
- **Zustand** for state
- **Radix UI** + **Tailwind CSS**

### Backend
- **FastAPI** + **Uvicorn**
- **SQLite** (app/library metadata in `backend/data/app.db`)
- **PostgreSQL + pgvector** (hybrid retrieval + RAG indexing)
- **MinIO / S3-compatible object storage** (optional durable PDF storage)
- **LiteLLM** for OpenAI/local providers
- **PyPDF** + **python-pptx** for document parsing
- **Ollama** for local LLMs
- **MCP Server** for tool-driven context uploads

## 📦 Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- Ollama for local LLMs

### Backend Setup (FastAPI)
```bash
python -m venv backend/.webenv
source backend/.webenv/bin/activate
pip install -r backend/requirements.txt
```

Create `backend/.env` (copy from `backend/.env.example`) and set your API keys and models:
```bash
cp backend/.env.example backend/.env
```

### Optional: MinIO Object Storage
If you want newly ingested library PDFs to be stored in MinIO instead of relying only on local files, run MinIO and set:

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_LIBRARY=library-docs
MINIO_SECURE=false
MINIO_AUTO_CREATE_BUCKET=true
```

Backfill existing local-library PDFs into MinIO:

```bash
backend/.webenv/bin/python backend/scripts/backfill_minio_assets.py
```

For the full storage design, asset roles, backfill/audit/repair flow, and MinIO-only fallback behavior, see:

- `docs/storage/minio.md`

### Frontend Setup (Vite)
```bash
npm install
```

Create a root `.env` for the frontend:
```env
VITE_API_BASE=http://localhost:8010/api
```

### Run the App
```bash
# Terminal 1 - Backend
source backend/.webenv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8010 --reload

# Terminal 2 - Frontend
npm run dev:client
```

Open the app at: **http://localhost:5173**

### MCP Server (local tool calls)
The MCP server powers tool-based context uploads for local LLMs.
```bash
source backend/.webenv/bin/activate
python -m backend.mcp_server.app
```
Set `LOCAL_MCP_SERVER_URL=http://127.0.0.1:8020/mcp` in `backend/.env`.

### ChatGPT SDK App
The ChatGPT SDK widget lives in `chatgpt-sdk-app/`. Follow `chatgpt-sdk-app/README.md` to run it independently.

## 📁 Data & Storage

- **SQLite DB**: `backend/data/app.db`
- **Downloaded PDFs**: `backend/data/pdfs/`
- **Exports**: `backend/exports/`
- **Search Benchmark Workspace**: `search_evaluation/`
- **MinIO Storage Notes**: `docs/storage/minio.md`

These are local artifacts and are not meant to be committed.

## 📁 Project Structure

```
Instructor-Assistant/
├── backend/               # FastAPI app, SQLite data, services
├── client/                # React + Vite SPA
├── docs/                  # Architecture and operational notes
├── modules/               # Reusable Python package(s), including ia_phase1
├── search_evaluation/     # Isolated search benchmark workspace
├── chatgpt-sdk-app/       # ChatGPT Apps SDK widget (optional)
└── attached_assets/       # Static assets for the frontend
```

## 🧩 Reusable Modules

- `modules/phase1-python/` contains the reusable `ia_phase1` package for ingestion and search helpers.
- `modules/phase1-python/README.md` documents package installation and usage.
- `Modularization.md` summarizes the currently extracted reusable features.

## 📊 Search Benchmarking

- `search_evaluation/` contains the isolated benchmark corpus, curated queries/gold labels, scripts, and reports for evaluating the active library search pipeline.
- Start with `search_evaluation/README.md` for the benchmark workflow.

## 📝 API Overview

Main endpoints (FastAPI):

- `/api/search` - Unified search across papers, sections, notes, and summaries
- `/api/papers` - List papers
- `/api/papers/download` - Download paper by DOI/URL
- `/api/papers/{id}/sections` - Paper sections or section-level matches inside one paper
- `/api/papers/{id}/context` - Extracted context
- `/api/papers/{id}/chat` - Paper Q&A / summarization
- `/api/papers/{id}/summaries` - Summary history per paper
- `/api/summaries/{id}` - Update/delete summaries
- `/api/notes` - Notes CRUD
- `/api/question-sets` - Question set CRUD
- `/api/question-sets/generate` - Generate questions (JSON)
- `/api/question-sets/generate/stream` - Streaming generation
- `/api/question-sets/context` - Upload PDF/PPT/PPTX for context
- `/api/rag/ingest` - Ingest library documents into PostgreSQL/pgvector
- `/api/rag/query` - RAG queries
- `/api/agent/chat` - Qwen agent chat

## 🐛 Troubleshooting

1. **API not reachable**
   - Ensure FastAPI is running on `http://localhost:8010`
   - Check `VITE_API_BASE` in the root `.env`
   - Ensure mcp server is running (python -m backend.mcp_server.app)

2. **Port conflicts**
   - Vite uses `5173`. See `PORT_FIX.md` for common macOS port issues.

3. **Local model issues**
   - Make sure Ollama is running: `ollama serve`
   - Verify `LOCAL_LLM_URL` and model names in `backend/.env`

## 📄 License

MIT License - see LICENSE file for details
