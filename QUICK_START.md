# Quick Start Guide - Instructor Assistant

## ✅ What's Included

The main app is a FastAPI backend + React/Vite frontend. Core features:

1. **Research Library** - Search, multi-select, summaries with history
2. **Notes Section** - Unified document library
3. **Question Sets** - Generate/edit/export with uploads (PDF/PPT/PPTX)
4. **RAG Page** - Selective ingestion, templates, query history
5. **Chat** - Agent chat with optional attachments

## 🚀 Running the Application

### 1) Backend (FastAPI)
```bash
python -m venv backend/.webenv
source backend/.webenv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env

uvicorn backend.main:app --host 0.0.0.0 --port 8010 --reload
```

### 2) Frontend (Vite)
```bash
npm install
```

Create a root `.env` with:
```env
VITE_API_BASE=http://localhost:8010/api
```

Then run:
```bash
npm run dev:client
```

The app will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8010/api

## 📍 Routes

- `/` - Chat Page
- `/library` - Research Library
- `/notes` - Notes
- `/questions` - Question Sets
- `/rag` - RAG

## MCP Server

```bash
source backend/.webenv/bin/activate
python -m backend.mcp_server.app
```

Set in `backend/.env`:
```
LOCAL_MCP_SERVER_URL=http://127.0.0.1:8020/mcp
```

## 🐛 Troubleshooting

If you encounter import errors:
1. Make sure all dependencies are installed: `npm install`
2. Check that all UI components exist in `client/src/components/ui/`
3. Verify TypeScript compilation: `npm run check`

## 📚 Documentation

- `README.md` - Full setup and architecture
- `IMPLEMENTATION_COMPLETE.md` - Implementation notes
- `PORT_FIX.md` - Port troubleshooting
