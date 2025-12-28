# ChatGPT Instructor Assistant – Web App

This repository contains the full-stack “Instructor Assistant” web app that helps faculty manage their research PDFs, annotate notes, and generate Canvas-ready question sets powered by OpenAI or a local Llama model.

## Features

- **Research Library** – Upload papers by DOI/URL/title, preview PDFs inline, delete entries, and summarize via an integrated chatbot that can save responses directly into the notes workspace.
- **Notes Workspace** – Notes UI with search, inline highlighting, and word counts. Any content from the notes can be searched globally.
- **Question Sets** – Dual workflow:
  - *Generate*: Upload source files, chat with the instructor assistant, and stream exam-ready questions + Markdown. Choose between OpenAI GPT and a local Llama 3.1 model with inline tool access.
  - *Upload*: Import existing Markdown, edit, or manage previously generated sets.
- **Canvas Export** – Save Markdown locally or push directly to Canvas with per-quiz settings (course, title, time limit, publish toggle).
- **Local LLM Support** – When `LLM_PROVIDER=local`, the backend orchestrates tool calls (`list_contexts`, `read_context`) so a local Llama model can read uploaded PDFs/PPTX excerpts before answering.
- **Qwen Agent Chat** – Floating chat bubble (bottom-right) that uses a local Qwen model (via Ollama) to pick and call tools automatically (web/news/arXiv/PDF/YouTube) and guide you to Research Library, Notes, or Question Sets.
- **RAG Utility** – PDF ingestion + FAISS index builder for retrieval-augmented generation (`backend/rag/ingest.py`; requires `langchain-text-splitters`, `langchain-community`, `faiss-cpu`).

## Repository Layout

```
backend/         # FastAPI app, LiteLLM/local LLM services, Canvas helper, context cache
client/          # React + Vite SPA (TypeScript)
chatgpt-sdk-app/ # ChatGPT Apps SDK widget (server + web)
```

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- (Optional) [Ollama](https://ollama.com/) or another local Llama runner
- An OpenAI API key for GPT-based generation

## Backend Setup

```bash
cd backend
python -m venv .webenv
source .webenv/bin/activate
pip install -r requirements.txt
```

Create `.env` with the desirable settings:

```dotenv
# OpenAI / LiteLLM
OPENAI_API_KEY=...
LITELLM_MODEL=gpt-5-mini

# Local LLM (via Ollama or compatible REST API)
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.1:8b

# Qwen agent (Ollama)
QWEN_AGENT_MODEL=qwen2.5:7b
# OLLAMA_HOST=http://127.0.0.1:11434

# Canvas integration
CANVAS_API_URL=...
CANVAS_ACCESS_TOKEN=...
```


### Running the API

```bash
cd backend
source .webenv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8010 --reload
```

This serves all REST endpoints under `http://localhost:8010/api`.

## Frontend Setup

```bash
cd client
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:5173`

## Local LLM Workflow

1. Launch your local runner (example with Ollama):
   ```bash
   ollama run llama3.1:8b
   ```
2. In the Question Sets page, pick “Local (Llama 3.1)” from the provider dropdown.
3. Upload PDFs/PPTX: the backend extracts text and stores it in `context_store`. The local LLM can call the inline tools to list and read excerpts before generating JSON.


### Local MCP Server for Question Sets

To start the MCP server for local LLM, run the following command from the root directory (make sure .webenv is activated):

```bash
python -m backend.mcp_server.app
```

Set `LOCAL_MCP_SERVER_URL` in the `.env` to the exposed `/mcp` endpoint (for example `http://127.0.0.1:8020/mcp`).

The server exposes these tools:

- `upload_context(filename, data_b64)` – send a base64-encoded PDF/PPT(X) file, which is extracted and added to the in-memory context store.
- `list_contexts()` – returns metadata (id, filename, length, preview) for every uploaded context.
- `read_context(context_id, start=0, length=4000)` – fetches a text slice from a context so the model can page through long documents.
- `delete_context(context_id)` – removes a context entry.
- `generate_question_set(instructions, context_ids?, provider?, question_count?, question_types?)` – invokes the shared `generate_questions` pipeline and returns the structured questions plus Canvas-ready Markdown.

## RAG Utility

If you want a local retrieval-augmented workflow, use `backend/rag/ingest.py` to ingest PDFs into a FAISS index. It loads PDFs, splits text, builds embeddings, and saves the index/metadata. Install extra deps:
```
pip install "langchain-text-splitters" "langchain-community" "faiss-cpu"
```
Then run the ingest flow in the UI.

## Qwen Agent Chat (Ollama)

The floating chat bubble in the web UI uses the local Qwen model (via Ollama) to automatically choose and call tools:

Tools available: DuckDuckGo web search, Google News RSS, arXiv search/download, PDF text extraction/summary, YouTube search/download.

Setup:
1. Pull and run Qwen in Ollama:
   ```bash
   ollama pull qwen2.5:7b
   ollama serve  # if not already running
   ```
2. Set env vars (in `.env`):
   ```
   QWEN_AGENT_MODEL=qwen2.5:7b
   # OLLAMA_HOST=http://127.0.0.1:11434   # only if not using default
   ```
3. Start the API and frontend as usual. The chat bubble will call the Qwen agent.


## Canvas Push Workflow

1. Configure the Canvas env vars.
2. Generate or upload a question set.
3. In the Markdown panel, open “Send to Canvas,” fill in quiz settings, and click “Push to Canvas.”  
   The backend creates the quiz, optional question groups, uploads all questions, and returns the Canvas URL.
