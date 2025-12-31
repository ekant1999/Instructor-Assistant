# Instructor Assistant

A full-stack web application that helps instructors manage research papers, generate summaries, build question sets, and query documents using RAG (Retrieval-Augmented Generation).

## 🎯 Features

### 📚 Research Library
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/42174f6e-ee1a-464e-b289-8d25edf2f275" />

- **Search & Filter**: Find papers by title, author, or keywords with real-time filtering
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
- **Selective Ingestion**: Choose which papers to index
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
- **SQLite** (local, in `backend/data/app.db`)
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

These are local artifacts and are not meant to be committed.

## 📁 Project Structure

```
Instructor-Assistant/
├── backend/               # FastAPI app, SQLite data, services
├── client/                # React + Vite SPA
├── chatgpt-sdk-app/        # ChatGPT Apps SDK widget (optional)
└── attached_assets/        # Static assets for the frontend
```

## 📝 API Overview

Main endpoints (FastAPI):

- `/api/papers` - List papers
- `/api/papers/download` - Download paper by DOI/URL
- `/api/papers/{id}/sections` - Paper sections
- `/api/papers/{id}/context` - Extracted context
- `/api/papers/{id}/chat` - Paper Q&A / summarization
- `/api/papers/{id}/summaries` - Summary history per paper
- `/api/summaries/{id}` - Update/delete summaries
- `/api/notes` - Notes CRUD
- `/api/question-sets` - Question set CRUD
- `/api/question-sets/generate` - Generate questions (JSON)
- `/api/question-sets/generate/stream` - Streaming generation
- `/api/question-sets/context` - Upload PDF/PPT/PPTX for context
- `/api/rag/ingest` - Build FAISS index
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
