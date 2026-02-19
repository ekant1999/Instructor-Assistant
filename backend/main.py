from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import threading
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.core.database import get_conn, init_db
from backend.core.postgres import init_db as init_pg_db
from backend.core.library import (
    render_library_structured,
    add_paper,
    add_web_page,
    delete_paper as delete_paper_record,
)
from backend.core.questions import (
    create_question_set,
    delete_question_set,
    get_question_set,
    list_question_sets,
    update_question_set,
)
from backend.core.search import (
    search_papers,
    search_sections,
    search_notes,
    search_summaries,
    search_all,
)
from backend.core.hybrid_search import hybrid_search, full_text_search
from backend.rag.pgvector_store import PgVectorStore

from .schemas import (
    CanvasPushRequest,
    CanvasPushResponse,
    NoteCreate,
    NoteUpdate,
    SummaryCreate,
    SummaryUpdate,
    PaperChatRequest,
    PaperDownloadRequest,
    PaperRecord,
    QuestionContextUploadResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    QuestionInsertionPreviewResponse,
    QuestionInsertionRequest,
    QuestionSetCreate,
    QuestionSetUpdate,
    AgentChatRequest,
    AgentChatResponse,
    WebSearchRequest,
    NewsRequest,
    ArxivSearchRequest,
    ArxivDownloadRequest,
    PdfSummaryRequest,
    YoutubeSearchRequest,
    YoutubeDownloadRequest,
    RAGIngestRequest,
    RAGIngestResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGIndexStatusResponse,
    RAGQnaCreateRequest,
    RAGQnaRecord,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from .services import (
    QuestionGenerationError,
    extract_context_from_upload,
    generate_insertion_preview,
    generate_questions,
    summarize_paper_chat,
    stream_generate_questions,
)
from .agent import run_agent
from .mcp_client import (
    MCPClientError,
    call_tool as call_mcp_tool,
    call_tool_async as call_mcp_tool_async,
    is_configured as mcp_configured,
)
from .canvas_service import CanvasPushError, push_question_set_to_canvas
from . import qwen_tools
from .rag import ingest_pgvector, query_pgvector, image_index, paper_figures, table_extractor
from backend.core.postgres import (
    get_pool as get_pg_pool,
    close_pool as close_pg_pool,
    normalize_timestamp,
)
from . import context_store

BACKEND_ROOT = Path(__file__).resolve().parent
DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BACKEND_ROOT / ".env", override=False)

logger = logging.getLogger(__name__)


def _parse_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, list):
        return [str(tag).strip() for tag in data if str(tag).strip()]
    return []


def _parse_metadata(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _sqlite_rank_score(raw: Any) -> float:
    try:
        if raw is None:
            return 0.0
        return -float(raw)
    except (TypeError, ValueError):
        return 0.0


def _pgvector_score(row: Dict[str, Any]) -> float:
    for key in ("hybrid_score", "similarity", "score"):
        val = row.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return 0.0


_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _query_tokens(query: str) -> List[str]:
    if not query:
        return []
    tokens = [t.lower() for t in _WORD_RE.findall(query) if len(t) > 2]
    # Deduplicate while preserving order
    return list(dict.fromkeys(tokens))


def _lexical_hits(tokens: List[str], text: str) -> int:
    if not tokens or not text:
        return 0
    text_lower = text.lower()
    return sum(1 for token in tokens if token in text_lower)


def _select_block_for_query(row: Dict[str, Any], tokens: List[str]) -> Dict[str, Any]:
    metadata = row.get("metadata")
    blocks = metadata.get("blocks") if isinstance(metadata, dict) else None
    if not blocks:
        return {
            "page_no": row.get("page_no"),
            "block_index": row.get("block_index"),
            "bbox": row.get("bbox"),
            "text": row.get("text") or "",
            "lex_hits": _lexical_hits(tokens, row.get("text") or ""),
        }

    best_block: Optional[Dict[str, Any]] = None
    best_hits = -1
    best_len = -1
    for block in blocks:
        text = block.get("text") or ""
        hits = _lexical_hits(tokens, text) if tokens else 0
        if hits > best_hits or (hits == best_hits and len(text) > best_len):
            best_block = block
            best_hits = hits
            best_len = len(text)

    if not best_block:
        return {
            "page_no": row.get("page_no"),
            "block_index": row.get("block_index"),
            "bbox": row.get("bbox"),
            "text": row.get("text") or "",
            "lex_hits": _lexical_hits(tokens, row.get("text") or ""),
        }

    return {
        "page_no": best_block.get("page_no") or row.get("page_no"),
        "block_index": best_block.get("block_index") or row.get("block_index"),
        "bbox": best_block.get("bbox") or row.get("bbox"),
        "text": best_block.get("text") or row.get("text") or "",
        "lex_hits": best_hits,
    }


def _build_match_snippet(query: str, tokens: List[str], text: str, max_len: int = 240) -> str:
    if not text:
        return ""
    clean = " ".join(text.replace("\x00", "").split())
    if not clean:
        return ""
    if not tokens:
        return clean[:max_len]
    lower = clean.lower()
    target_tokens = [t for t in tokens if t in lower]
    if target_tokens:
        # Find the smallest window that covers all present query tokens.
        words = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_RE.finditer(clean)]
        target_set = set(target_tokens)
        needed = len(target_set)
        counts: Dict[str, int] = {}
        have = 0
        best_window: Optional[tuple[int, int]] = None
        left = 0
        for right, (token, start, end) in enumerate(words):
            if token in target_set:
                counts[token] = counts.get(token, 0) + 1
                if counts[token] == 1:
                    have += 1
            while have == needed and left <= right:
                window_start = words[left][1]
                window_end = end
                if best_window is None or (window_end - window_start) < (best_window[1] - best_window[0]):
                    best_window = (window_start, window_end)
                left_token = words[left][0]
                if left_token in target_set:
                    counts[left_token] -= 1
                    if counts[left_token] == 0:
                        have -= 1
                left += 1
        if best_window:
            pad = 12
            start = max(0, best_window[0] - pad)
            end = min(len(clean), best_window[1] + pad)
            snippet = clean[start:end]
            if len(snippet) <= max_len:
                return snippet
            clean = snippet
            lower = clean.lower()

    tokens_sorted = sorted(tokens, key=len, reverse=True)
    anchor = -1
    for token in tokens_sorted:
        idx = lower.find(token)
        if idx != -1:
            anchor = idx
            break
    if anchor == -1:
        return clean[:max_len]
    target_len = min(max_len, max(60, len(query) * 2))
    start = max(0, anchor - target_len // 4)
    if start > 0:
        prior_space = clean.rfind(" ", 0, start)
        if prior_space != -1:
            start = prior_space + 1
    end = min(len(clean), start + target_len)
    if end < len(clean):
        next_space = clean.find(" ", end)
        if next_space != -1:
            end = next_space
    return clean[start:end]


def _looks_like_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _build_web_blocks(paper_id: int, source_url: Optional[str], title: Optional[str]) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT page_no, text FROM sections WHERE paper_id=? ORDER BY page_no ASC",
            (paper_id,),
        ).fetchall()
    blocks: List[Dict[str, Any]] = []
    for row in rows:
        text = (row["text"] or "").replace("\x00", "").strip()
        if not text:
            continue
        blocks.append(
            {
                "page_no": row["page_no"],
                "block_index": 0,
                "text": text,
                "bbox": None,
                "metadata": {
                    "source_type": "web",
                    "source_url": source_url,
                    "paper_title": title,
                },
            }
        )
    return blocks


async def _ingest_web_papers(papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not papers:
        return {"papers_ingested": 0, "total_chunks": 0, "failed": []}
    total_chunks = 0
    failed: List[Dict[str, Any]] = []
    for paper in papers:
        try:
            blocks = _build_web_blocks(paper["id"], paper.get("source_url"), paper.get("title"))
            if not blocks:
                raise RuntimeError("No text sections available for web document.")
            result = await ingest_pgvector.ingest_blocks(
                blocks=blocks,
                paper_id=paper["id"],
                paper_title=paper.get("title") or "Untitled",
            )
            total_chunks += result.get("num_chunks", len(blocks))
        except Exception as exc:
            failed.append(
                {
                    "paper_id": paper.get("id"),
                    "title": paper.get("title"),
                    "error": str(exc),
                }
            )
    return {
        "papers_ingested": len(papers) - len(failed),
        "total_papers": len(papers),
        "total_chunks": total_chunks,
        "failed": failed,
        "success": len(failed) == 0,
    }


def _pgvector_search_paper_ids(query: str, search_type: str, limit: int = 100) -> Dict[int, float]:
    async def _run() -> Dict[int, float]:
        alpha_raw = os.getenv("HYBRID_SEARCH_ALPHA", "0.5")
        try:
            alpha = float(alpha_raw)
        except ValueError:
            alpha = 0.5
        pool = await get_pg_pool()
        store = PgVectorStore(pool)
        retrieve_k = max(20, min(limit * 5, 300))
        if search_type == "embedding":
            results = await store.similarity_search(query, k=retrieve_k)
        elif search_type == "keyword":
            results = await full_text_search(query, pool, k=retrieve_k)
        else:
            results = await hybrid_search(query, store, pool, k=retrieve_k, alpha=alpha)
        score_by_id: Dict[int, float] = {}
        for row in results or []:
            pid = row.get("paper_id")
            if pid is None:
                continue
            score = _pgvector_score(row)
            prev = score_by_id.get(pid)
            if prev is None or score > prev:
                score_by_id[pid] = score
        return score_by_id

    try:
        return asyncio.run(_run())
    except Exception:
        logger.exception("pgvector search failed; falling back to SQLite search")
        return {}
    finally:
        try:
            asyncio.run(close_pg_pool())
        except Exception:
            pass


def _pgvector_search_sections(
    paper_id: int,
    query: str,
    search_type: str,
    include_text: bool,
    max_chars: Optional[int],
    limit: int = 100,
) -> List[Dict[str, Any]]:
    async def _run() -> List[Dict[str, Any]]:
        alpha_raw = os.getenv("HYBRID_SEARCH_ALPHA", "0.5")
        try:
            alpha = float(alpha_raw)
        except ValueError:
            alpha = 0.5
        pool = await get_pg_pool()
        store = PgVectorStore(pool)
        retrieve_k = max(20, min(limit * 5, 300))
        if search_type == "embedding":
            return await store.similarity_search(query, k=retrieve_k, paper_ids=[paper_id])
        if search_type == "keyword":
            return await full_text_search(query, pool, k=retrieve_k, paper_ids=[paper_id])
        return await hybrid_search(query, store, pool, k=retrieve_k, paper_ids=[paper_id], alpha=alpha)

    try:
        results = asyncio.run(_run())
    except Exception:
        logger.exception("pgvector section search failed; falling back to SQLite search")
        return []
    finally:
        try:
            asyncio.run(close_pg_pool())
        except Exception:
            pass

    if not results:
        return []

    tokens = _query_tokens(query)
    page_scores: Dict[int, float] = {}
    page_best: Dict[int, Dict[str, Any]] = {}
    page_best_lex: Dict[int, Dict[str, Any]] = {}
    for row in results:
        match_block = _select_block_for_query(row, tokens)
        page_no = match_block.get("page_no") or row.get("page_no")
        if not page_no:
            continue
        score = _pgvector_score(row)
        page_no_int = int(page_no)
        prev = page_scores.get(page_no_int)
        if prev is None or score > prev:
            page_scores[page_no_int] = score
            page_best[page_no_int] = {
                "bbox": match_block.get("bbox") or row.get("bbox"),
                "block_index": match_block.get("block_index") or row.get("block_index"),
                "text": match_block.get("text") or row.get("text"),
                "lex_hits": match_block.get("lex_hits", 0),
            }

        lex_hits = match_block.get("lex_hits", 0)
        prev_lex = page_best_lex.get(page_no_int)
        if prev_lex is None or lex_hits > prev_lex.get("lex_hits", 0):
            page_best_lex[page_no_int] = {
                "bbox": match_block.get("bbox") or row.get("bbox"),
                "block_index": match_block.get("block_index") or row.get("block_index"),
                "text": match_block.get("text") or row.get("text"),
                "lex_hits": lex_hits,
            }

    if not page_scores:
        return []

    pages = list(page_scores.keys())
    placeholders = ",".join("?" for _ in pages)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, page_no, text
            FROM sections
            WHERE paper_id=? AND page_no IN ({placeholders})
            """,
            (paper_id, *pages),
        ).fetchall()

    sections: List[Dict[str, Any]] = []
    for r in rows:
        best = page_best.get(r["page_no"]) or {}
        lex = page_best_lex.get(r["page_no"])
        if lex and tokens:
            min_hits = 1 if len(tokens) <= 3 else 2
            if lex.get("lex_hits", 0) >= min_hits:
                best = lex
        entry = {
            "id": r["id"],
            "page_no": r["page_no"],
            "paper_id": paper_id,
            "match_score": page_scores.get(r["page_no"], 0),
            "match_bbox": best.get("bbox"),
            "match_block_index": best.get("block_index"),
        }
        best_text = best.get("text") or ""
        match_text = _build_match_snippet(query, tokens, best_text)
        if match_text:
            entry["match_text"] = match_text
        if include_text:
            text = r["text"] or ""
            if max_chars is not None and max_chars > 0:
                text = text[:max_chars]
            entry["text"] = text
        sections.append(entry)

    sections.sort(key=lambda item: item.get("match_score", 0), reverse=True)
    return sections


def _get_paper(paper_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at FROM papers WHERE id=?",
            (paper_id,)
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    pdf_path = data.get("pdf_path")
    data["pdf_url"] = f"/papers/{data['id']}/file" if pdf_path else None
    return data

app = FastAPI(title="Instructor Assistant Web API")

RAG_INGEST_THREAD: Optional[threading.Thread] = None
RAG_INGEST_PENDING = False


def _pdf_frame_ancestors() -> str:
    extras = [o.strip() for o in os.getenv("PDF_FRAME_ANCESTORS", "").split(",") if o.strip()]
    allowed = [
        "'self'",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "https://chatgpt.com",
        "https://chat.openai.com",
        *extras,
    ]
    return "frame-ancestors " + " ".join(allowed)


def _parse_rag_sources(raw: Optional[str]) -> List[Dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    return []


def _as_json_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _as_json_list(raw: Any) -> List[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if isinstance(parsed, list):
            return parsed
    return []


def _set_rag_status(paper_ids: List[int], status: str, error: Optional[str] = None) -> None:
    if not paper_ids:
        return
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in paper_ids)
        params = [status, error, *paper_ids]
        conn.execute(
            f"UPDATE papers SET rag_status=?, rag_error=?, rag_updated_at=datetime('now') WHERE id IN ({placeholders})",
            params,
        )
        conn.commit()


def _set_all_rag_status(status: str, error: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET rag_status=?, rag_error=?, rag_updated_at=datetime('now')",
            (status, error),
        )
        conn.commit()


def _collect_rag_papers() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at
            FROM papers
            """
        ).fetchall()
    return [dict(r) for r in rows]


async def _upsert_pg_papers(papers: List[Dict[str, Any]]) -> None:
    if not papers:
        return
    pool = await get_pg_pool()
    payload = []
    for p in papers:
        payload.append(
            (
                p.get("id"),
                p.get("title"),
                p.get("source_url"),
                p.get("pdf_path"),
                p.get("rag_status"),
                p.get("rag_error"),
                normalize_timestamp(p.get("rag_updated_at")),
                normalize_timestamp(p.get("created_at")),
            )
        )
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO papers (id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                source_url = EXCLUDED.source_url,
                pdf_path = EXCLUDED.pdf_path,
                rag_status = EXCLUDED.rag_status,
                rag_error = EXCLUDED.rag_error,
                rag_updated_at = EXCLUDED.rag_updated_at
            """,
            payload,
        )


def _run_full_rag_ingestion() -> None:
    papers = _collect_rag_papers()
    if not papers:
        return

    paper_ids = [p["id"] for p in papers]
    pdf_papers = [p for p in papers if p.get("pdf_path")]
    web_papers = [p for p in papers if not p.get("pdf_path")]
    pdf_paths = [p["pdf_path"] for p in pdf_papers if p.get("pdf_path")]
    metadata_by_path = {
        str(Path(p["pdf_path"]).expanduser().resolve()): {
            "paper_id": p["id"],
            "paper_title": p.get("title") or Path(p["pdf_path"]).stem,
        }
        for p in pdf_papers
        if p.get("pdf_path")
    }
    _set_rag_status(paper_ids, "processing", None)

    try:
        async def _ingest() -> Dict[str, Any]:
            try:
                await _upsert_pg_papers(papers)
                pdf_result: Dict[str, Any] = {"papers_ingested": 0, "total_chunks": 0, "failed": []}
                if pdf_papers:
                    pdf_ids = [p["id"] for p in pdf_papers]
                    pdf_result = await ingest_pgvector.ingest_papers_from_db(
                        paper_ids=pdf_ids,
                        chunk_size=1200,
                        chunk_overlap=200,
                    )
                web_result = await _ingest_web_papers(web_papers)
                return {"pdf": pdf_result, "web": web_result}
            finally:
                await close_pg_pool()

        result = asyncio.run(_ingest())
        if os.getenv("ENABLE_IMAGE_INDEX", "true").lower() in {"1", "true", "yes"}:
            image_index_dir = os.getenv("IMAGE_INDEX_DIR", str(BACKEND_ROOT / "index_images"))
            figure_dir = os.getenv("FIGURE_OUTPUT_DIR", str(DATA_DIR / "figures"))
            try:
                image_index.build_image_index(pdf_paths, metadata_by_path, figure_dir, image_index_dir)
            except Exception as exc:
                logger.exception("Image indexing failed: %s", exc)
        failed: List[Dict[str, Any]] = []
        for key in ("pdf", "web"):
            failed.extend(result.get(key, {}).get("failed") or [])
        failed_ids = {f.get("paper_id") for f in failed if f.get("paper_id")}
        success_ids = [pid for pid in paper_ids if pid not in failed_ids]
        if success_ids:
            _set_rag_status(success_ids, "done", None)
        for f in failed:
            pid = f.get("paper_id")
            if pid is not None:
                _set_rag_status([pid], "error", str(f.get("error") or "Ingestion failed")[:500])
        total_ingested = result.get("pdf", {}).get("papers_ingested", 0) + result.get("web", {}).get("papers_ingested", 0)
        logger.info("RAG ingestion complete for %s papers", total_ingested)
    except Exception as exc:
        logger.exception("RAG ingestion failed")
        _set_rag_status(paper_ids, "error", str(exc))


def _rag_ingest_worker() -> None:
    global RAG_INGEST_PENDING
    while True:
        _run_full_rag_ingestion()
        if RAG_INGEST_PENDING:
            RAG_INGEST_PENDING = False
            continue
        break


def schedule_rag_rebuild() -> None:
    global RAG_INGEST_THREAD, RAG_INGEST_PENDING
    papers = _collect_rag_papers()
    if not papers:
        return
    _set_all_rag_status("queued", None)
    if RAG_INGEST_THREAD and RAG_INGEST_THREAD.is_alive():
        RAG_INGEST_PENDING = True
        return
    RAG_INGEST_PENDING = False
    RAG_INGEST_THREAD = threading.Thread(target=_rag_ingest_worker, daemon=True)
    RAG_INGEST_THREAD.start()



@app.on_event("startup")
async def _startup() -> None:
    init_db()
    try:
        await init_pg_db()
    except Exception:
        logger.exception("PostgreSQL init failed; pgvector features may be unavailable.")

cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://chat.openai.com",
    "https://chatgpt.com",
    "null",
]
extra_origins = [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]
cors_origin_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX", r".*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins + extra_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def search_endpoint(payload: SearchRequest) -> SearchResponse:
    """
    Unified search endpoint that searches across papers, sections, notes, and summaries.
    
    Supports keyword-based (FTS5), embedding-based (FAISS), or hybrid search.
    """
    search_type = payload.search_type or "keyword"
    if search_type not in ["keyword", "embedding", "hybrid"]:
        search_type = "keyword"
    
    # Search all categories
    all_results = search_all(
        payload.query,
        search_type=search_type,
        paper_ids=payload.paper_ids,
        limit_per_category=payload.limit,
    )
    
    # Combine and format results
    combined_results: List[SearchResult] = []
    
    for paper in all_results.get("papers", []):
        combined_results.append(
            SearchResult(
                id=paper["id"],
                relevance_score=paper.get("rank"),
                result_type="paper",
                data=paper,
            )
        )
    
    for section in all_results.get("sections", []):
        combined_results.append(
            SearchResult(
                id=section["id"],
                relevance_score=section.get("rank"),
                result_type="section",
                data=section,
            )
        )
    
    for note in all_results.get("notes", []):
        note_data = dict(note)
        note_data["tags"] = _parse_tags(note_data.pop("tags_json", None))
        combined_results.append(
            SearchResult(
                id=note["id"],
                relevance_score=note.get("rank"),
                result_type="note",
                data=note_data,
            )
        )
    
    for summary in all_results.get("summaries", []):
        summary_data = dict(summary)
        summary_data["metadata"] = _parse_metadata(summary_data.pop("metadata_json", None))
        summary_data["is_edited"] = bool(summary_data.get("is_edited"))
        combined_results.append(
            SearchResult(
                id=summary["id"],
                relevance_score=summary.get("rank"),
                result_type="summary",
                data=summary_data,
            )
        )
    
    return SearchResponse(
        query=payload.query,
        search_type=search_type,
        results=combined_results,
        total_results=len(combined_results),
    )


@app.get("/api/papers")
def list_papers(
    q: Optional[str] = None,
    search_type: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """
    List all papers or search papers with query parameter.
    
    Query params:
        q: Optional search query
        search_type: "keyword", "embedding", or "hybrid" (defaults to "keyword")
    
    When searching, returns papers that match in either:
    - Paper title/source
    - PDF content (sections)
    """
    if q:
        # Search papers by title AND sections
        st = search_type or "keyword"
        if st not in ["keyword", "embedding", "hybrid"]:
            st = "keyword"

        score_by_id: Dict[int, float] = {}
        matching_paper_ids: set[int] = set()

        # Keyword search over titles/URLs (SQLite FTS)
        paper_results = []
        if st in ["keyword", "hybrid"]:
            paper_results = search_papers(q, search_type="keyword", limit=100)
            for p in paper_results:
                pid = p.get("id")
                if pid is None:
                    continue
                matching_paper_ids.add(pid)
                score_by_id[pid] = max(score_by_id.get(pid, float("-inf")), _sqlite_rank_score(p.get("rank")))

        # Keyword search over sections (SQLite FTS)
        section_results = []
        if st in ["keyword", "hybrid"]:
            section_results = search_sections(q, search_type="keyword", limit=500)
            for s in section_results:
                pid = s.get("paper_id")
                if pid is None:
                    continue
                matching_paper_ids.add(pid)
                score_by_id[pid] = max(score_by_id.get(pid, float("-inf")), _sqlite_rank_score(s.get("rank")))

        # pgvector semantic/hybrid search over text_blocks (PostgreSQL)
        if st in ["embedding", "hybrid"]:
            pg_scores = _pgvector_search_paper_ids(q, st, limit=100)
            for pid, score in pg_scores.items():
                matching_paper_ids.add(pid)
                score_by_id[pid] = max(score_by_id.get(pid, float("-inf")), score)

        # Fetch full paper details for all matching papers
        if matching_paper_ids:
            with get_conn() as conn:
                placeholders = ','.join('?' for _ in matching_paper_ids)
                rows = conn.execute(
                    f"""
                    SELECT id, title, source_url, pdf_path, rag_status, rag_error, 
                           rag_updated_at, created_at
                    FROM papers
                    WHERE id IN ({placeholders})
                    ORDER BY datetime(created_at) DESC
                    """,
                    tuple(matching_paper_ids)
                ).fetchall()
                papers = [dict(row) for row in rows]
                
                # Add pdf_url field for frontend compatibility
                for p in papers:
                    pdf_path = p.get("pdf_path")
                    p["pdf_url"] = f"/papers/{p['id']}/file" if pdf_path else None

                if score_by_id:
                    papers.sort(
                        key=lambda p: score_by_id.get(p["id"], float("-inf")),
                        reverse=True,
                    )
        else:
            papers = []
        
        return {"papers": papers}
    else:
        # Return all papers
        data = render_library_structured()
        return {"papers": data.get("papers", [])}


@app.get("/api/papers/{paper_id}/file")
def download_paper_file(paper_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT title, pdf_path FROM papers WHERE id=?", (paper_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found.")
    raw_pdf_path = row["pdf_path"] or ""
    if not raw_pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available on server.")
    pdf_path = Path(raw_pdf_path).expanduser()
    if not pdf_path.exists():
        fallback = DATA_DIR / "pdfs" / pdf_path.name
        if fallback.exists():
            pdf_path = fallback
            with get_conn() as conn:
                conn.execute("UPDATE papers SET pdf_path=? WHERE id=?", (str(pdf_path), paper_id))
        else:
            raise HTTPException(status_code=404, detail="PDF not available on server.")
    headers = {
        "Content-Disposition": f"inline; filename=\"{pdf_path.name}\"",
        "Content-Security-Policy": _pdf_frame_ancestors(),
        "Cross-Origin-Resource-Policy": "cross-origin",
    }
    return FileResponse(pdf_path, media_type="application/pdf", headers=headers)


@app.get("/api/papers/{paper_id}/sections")
def list_paper_sections(
    paper_id: int,
    include_text: bool = True,
    max_chars: Optional[int] = None,
    q: Optional[str] = None,
    search_type: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    List all sections for a paper or search sections with query parameter.
    
    Query params:
        include_text: Include full text content
        max_chars: Truncate text to this many characters
        q: Optional search query
        search_type: "keyword", "embedding", or "hybrid" (defaults to "keyword")
    """
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Paper not found.")

    if q:
        # Search sections
        st = search_type or "keyword"
        if st not in ["keyword", "embedding", "hybrid"]:
            st = "keyword"

        # For hybrid searches, prefer exact keyword hits when available.
        if st == "hybrid":
            keyword_results = search_sections(q, search_type="keyword", paper_ids=[paper_id], limit=100)
            if keyword_results:
                sections: List[Dict[str, Any]] = []
                for r in keyword_results:
                    entry = {
                        "id": r["id"],
                        "page_no": r["page_no"],
                        "paper_id": r["paper_id"],
                        "match_score": r.get("rank", 0),
                    }
                    if include_text:
                        text = r["text"] or ""
                        if max_chars is not None and max_chars > 0:
                            text = text[:max_chars]
                        entry["text"] = text
                    sections.append(entry)
                return {"sections": sections}

        # Use pgvector for embedding/hybrid searches when keyword has no hits
        if st in ["embedding", "hybrid"]:
            pg_sections = _pgvector_search_sections(
                paper_id,
                q,
                st,
                include_text=include_text,
                max_chars=max_chars,
                limit=100,
            )
            if pg_sections:
                return {"sections": pg_sections}
            if st == "embedding":
                return {"sections": []}
            # fall back to keyword if hybrid found nothing
            st = "keyword"

        results = search_sections(q, search_type="keyword", paper_ids=[paper_id], limit=100)
        sections: List[Dict[str, Any]] = []
        for r in results:
            entry = {
                "id": r["id"],
                "page_no": r["page_no"],
                "paper_id": r["paper_id"],
                "match_score": r.get("rank", 0)  # Include relevance score for highlighting
            }
            if include_text:
                text = r["text"] or ""
                if max_chars is not None and max_chars > 0:
                    text = text[:max_chars]
                entry["text"] = text
            sections.append(entry)
        return {"sections": sections}
    else:
        # Return all sections
        with get_conn() as conn:
            if include_text:
                rows = conn.execute(
                    "SELECT id, page_no, text FROM sections WHERE paper_id=? ORDER BY page_no ASC",
                    (paper_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, page_no FROM sections WHERE paper_id=? ORDER BY page_no ASC",
                    (paper_id,),
                ).fetchall()

        sections: List[Dict[str, Any]] = []
        for r in rows:
            entry = {"id": r["id"], "page_no": r["page_no"]}
            if include_text:
                text = r["text"] or ""
                if max_chars is not None and max_chars > 0:
                    text = text[:max_chars]
                entry["text"] = text
            sections.append(entry)
        return {"sections": sections}


@app.get("/api/papers/{paper_id}/context")
def get_paper_context(
    paper_id: int,
    section_ids: Optional[str] = None,
    max_chars: int = 60000,
) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Paper not found.")

        ids: Optional[List[int]] = None
        if section_ids:
            try:
                ids = [int(s) for s in section_ids.split(",") if s.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="section_ids must be a comma-separated list of integers.")

        if ids:
            placeholders = ",".join("?" for _ in ids)
            query_sql = f"""
                SELECT page_no, text FROM sections
                WHERE paper_id=? AND id IN ({placeholders})
                ORDER BY page_no ASC
            """
            rows = conn.execute(query_sql, (paper_id, *ids)).fetchall()
        else:
            rows = conn.execute(
                "SELECT page_no, text FROM sections WHERE paper_id=? ORDER BY page_no ASC",
                (paper_id,),
            ).fetchall()

    context = "\n\n".join((r["text"] or "" for r in rows)).strip()
    if max_chars and max_chars > 0:
        context = context[:max_chars]
    return {"paper_id": paper_id, "context": context}


@app.get("/api/papers/{paper_id}/ingestion-info")
async def get_paper_ingestion_info(
    paper_id: int,
    chunk_limit: int = 120,
) -> Dict[str, Any]:
    """
    Debug endpoint for viewing extracted section/chunk metadata for a paper.

    This is intended for temporary inspection in the library UI.
    """
    if chunk_limit < 1 or chunk_limit > 1000:
        raise HTTPException(status_code=400, detail="chunk_limit must be between 1 and 1000.")

    paper = _get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    table_manifest = table_extractor.load_paper_table_manifest(paper_id)
    table_entries_raw = table_manifest.get("tables") or []
    table_entries = table_entries_raw if isinstance(table_entries_raw, list) else []
    table_preview_max_rows = 8
    table_preview_max_cell_chars = 240
    table_preview_max_header_chars = 120
    table_items = [
        {
            "id": int(item.get("id") or 0),
            "page_no": int(item.get("page_no") or 0),
            "n_rows": int(item.get("n_rows") or 0),
            "n_cols": int(item.get("n_cols") or 0),
            "caption": str(item.get("caption") or "").strip() or None,
            "section_canonical": str(item.get("section_canonical") or "other"),
            "section_source": str(item.get("section_source") or "unknown"),
            "section_confidence": item.get("section_confidence"),
            "markdown_preview": str(item.get("markdown") or "").strip()[:1500] or None,
            "headers_preview": [
                str(cell or "").strip()[:table_preview_max_header_chars]
                for cell in (item.get("headers") if isinstance(item.get("headers"), list) else [])
            ],
            "rows_preview": [
                [
                    str(cell or "").strip()[:table_preview_max_cell_chars]
                    for cell in (row if isinstance(row, list) else [])
                ]
                for row in (
                    item.get("rows")[:table_preview_max_rows]
                    if isinstance(item.get("rows"), list)
                    else []
                )
                if isinstance(row, list)
            ],
            "preview_truncated": (
                len(item.get("rows"))
                if isinstance(item.get("rows"), list)
                else 0
            ) > table_preview_max_rows,
        }
        for item in table_entries
        if isinstance(item, dict)
    ]

    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            total_chunks = int(
                await conn.fetchval(
                    "SELECT COUNT(*) FROM text_blocks WHERE paper_id=$1",
                    paper_id,
                )
                or 0
            )
            rows = []
            if total_chunks:
                rows = await conn.fetch(
                    """
                    SELECT id, page_no, block_index, text, bbox, metadata
                    FROM text_blocks
                    WHERE paper_id=$1
                    ORDER BY page_no ASC, block_index ASC
                    LIMIT $2
                    """,
                    paper_id,
                    chunk_limit,
                )
    except Exception as exc:
        logger.exception("Failed to load ingestion info for paper %s", paper_id)
        raise HTTPException(status_code=500, detail=str(exc))

    if not total_chunks:
        with get_conn() as conn:
            sqlite_sections = conn.execute(
                "SELECT COUNT(*) FROM sections WHERE paper_id=?",
                (paper_id,),
            ).fetchone()
            sqlite_section_count = int(sqlite_sections[0] if sqlite_sections else 0)
        logger.info(
            "Paper %s ingestion info: no pgvector chunks (sqlite_sections=%s, tables=%s)",
            paper_id,
            sqlite_section_count,
            len(table_items),
        )
        return {
            "paper_id": paper_id,
            "paper_title": paper.get("title"),
            "source_url": paper.get("source_url"),
            "pdf_url": paper.get("pdf_url"),
            "total_chunks": 0,
            "returned_chunks": 0,
            "chunk_limit": chunk_limit,
            "truncated": False,
            "sections": [],
            "chunks": [],
            "num_tables": len(table_items),
            "tables": table_items,
            "sqlite_section_count": sqlite_section_count,
            "message": "No pgvector chunks found for this paper. Run ingestion/indexing first.",
        }

    section_accumulator: Dict[str, Dict[str, Any]] = {}
    source_counts: Dict[str, int] = {}
    chunk_items: List[Dict[str, Any]] = []

    for row in rows:
        metadata = _as_json_dict(row["metadata"])
        bbox = _as_json_dict(row["bbox"]) if row["bbox"] is not None else None
        text = (row["text"] or "").replace("\x00", "")
        text_preview = " ".join(text.split())[:320]

        section_primary = str(metadata.get("section_primary") or metadata.get("section_canonical") or "").strip()
        section_all = metadata.get("section_all")
        if not isinstance(section_all, list):
            section_all = [section_primary] if section_primary else []
        section_all = [str(item).strip() for item in section_all if str(item).strip()]

        section_titles = metadata.get("section_titles")
        if not isinstance(section_titles, list):
            section_titles = [metadata.get("section_title")] if metadata.get("section_title") else []
        section_titles = [str(item).strip() for item in section_titles if str(item).strip()]

        section_source = str(metadata.get("section_source") or "unknown").strip() or "unknown"
        section_confidence = metadata.get("section_confidence")
        source_counts[section_source] = source_counts.get(section_source, 0) + 1

        row_page = int(row["page_no"])
        row_block_index = int(row["block_index"])

        def _get_bucket(canonical: str) -> Dict[str, Any]:
            return section_accumulator.setdefault(
                canonical,
                {
                    "canonical": canonical,
                    "chunk_count": 0,
                    "pages": set(),
                    "titles": set(),
                    "source_counts": {},
                    "confidence_sum": 0.0,
                    "confidence_count": 0,
                    "first_page": row_page,
                    "first_block_index": row_block_index,
                },
            )

        block_items = _as_json_list(metadata.get("blocks"))
        chunk_memberships: set[str] = set()

        for block in block_items:
            if not isinstance(block, dict):
                continue
            block_meta = block.get("metadata")
            block_meta = block_meta if isinstance(block_meta, dict) else {}
            canonical = str(block_meta.get("section_canonical") or "").strip()
            if not canonical:
                canonical = section_primary or "other"
            page_no = int(block.get("page_no") or row_page)
            block_index = int(block.get("block_index") or 0)
            title = str(block_meta.get("section_title") or "").strip()
            if not title and section_titles:
                title = section_titles[0]
            source_name = str(block_meta.get("section_source") or section_source).strip() or "unknown"
            confidence = block_meta.get("section_confidence")
            if not isinstance(confidence, (int, float)):
                confidence = section_confidence

            bucket = _get_bucket(canonical)
            bucket["pages"].add(page_no)
            if (
                page_no < bucket["first_page"]
                or (page_no == bucket["first_page"] and block_index < bucket["first_block_index"])
            ):
                bucket["first_page"] = page_no
                bucket["first_block_index"] = block_index
            if title:
                bucket["titles"].add(title)
            source_bucket = bucket["source_counts"]
            source_bucket[source_name] = source_bucket.get(source_name, 0) + 1
            if isinstance(confidence, (int, float)):
                bucket["confidence_sum"] += float(confidence)
                bucket["confidence_count"] += 1
            chunk_memberships.add(canonical)

        if not chunk_memberships:
            for canonical in section_all or [section_primary or "other"]:
                bucket = _get_bucket(canonical)
                bucket["pages"].add(row_page)
                if (
                    row_page < bucket["first_page"]
                    or (row_page == bucket["first_page"] and row_block_index < bucket["first_block_index"])
                ):
                    bucket["first_page"] = row_page
                    bucket["first_block_index"] = row_block_index
                for title in section_titles:
                    bucket["titles"].add(title)
                source_bucket = bucket["source_counts"]
                source_bucket[section_source] = source_bucket.get(section_source, 0) + 1
                if isinstance(section_confidence, (int, float)):
                    bucket["confidence_sum"] += float(section_confidence)
                    bucket["confidence_count"] += 1
                chunk_memberships.add(canonical)

        for canonical in chunk_memberships:
            bucket = _get_bucket(canonical)
            bucket["chunk_count"] += 1

        chunk_items.append(
            {
                "id": int(row["id"]),
                "page_no": int(row["page_no"]),
                "block_index": int(row["block_index"]),
                "char_count": len(text),
                "text_preview": text_preview,
                "bbox": bbox,
                "section_primary": section_primary,
                "section_all": section_all,
                "section_titles": section_titles,
                "metadata_summary": {
                    "chunk_type": metadata.get("chunk_type"),
                    "section_source": section_source,
                    "section_confidence": section_confidence,
                    "spans_multiple_sections": metadata.get("spans_multiple_sections"),
                    "block_count": len(metadata.get("blocks") or []) if isinstance(metadata.get("blocks"), list) else 0,
                },
                "metadata": metadata,
            }
        )

    sections: List[Dict[str, Any]] = []
    for canonical, payload in section_accumulator.items():
        source_items = sorted(
            payload["source_counts"].items(),
            key=lambda item: item[1],
            reverse=True,
        )
        primary_source = source_items[0][0] if source_items else "unknown"
        avg_confidence = None
        if payload["confidence_count"] > 0:
            avg_confidence = round(payload["confidence_sum"] / payload["confidence_count"], 3)
        sections.append(
            {
                "canonical": canonical,
                "chunk_count": payload["chunk_count"],
                "pages": sorted(payload["pages"]),
                "first_page": payload["first_page"],
                "first_block_index": payload["first_block_index"],
                "title_samples": sorted(payload["titles"])[:8],
                "primary_source": primary_source,
                "source_counts": [
                    {"source": source, "count": count}
                    for source, count in source_items
                ],
                "avg_confidence": avg_confidence,
            }
        )

    sections.sort(
        key=lambda item: (
            item.get("first_page", 10**9),
            item.get("first_block_index", 10**9),
            item.get("canonical", ""),
        )
    )
    source_summary = sorted(source_counts.items(), key=lambda item: item[1], reverse=True)
    strategy = source_summary[0][0] if source_summary else "unknown"
    logger.info(
        "Paper %s ingestion info: strategy=%s sources=%s tables=%s returned_chunks=%s total_chunks=%s",
        paper_id,
        strategy,
        ", ".join(f"{source} ({count})" for source, count in source_summary) or "n/a",
        len(table_items),
        len(chunk_items),
        total_chunks,
    )

    return {
        "paper_id": paper_id,
        "paper_title": paper.get("title"),
        "source_url": paper.get("source_url"),
        "pdf_url": paper.get("pdf_url"),
        "total_chunks": total_chunks,
        "returned_chunks": len(chunk_items),
        "chunk_limit": chunk_limit,
        "truncated": total_chunks > len(chunk_items),
        "section_strategy": strategy,
        "section_source_summary": [
            {"source": source, "count": count}
            for source, count in source_summary
        ],
        "sections": sections,
        "chunks": chunk_items,
        "num_tables": len(table_items),
        "tables": table_items,
    }


@app.get("/api/papers/{paper_id}/figures/{figure_name}")
def get_paper_figure_file(paper_id: int, figure_name: str):
    paper = _get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    try:
        figure_path = paper_figures.resolve_figure_file(paper_id, figure_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not figure_path.exists():
        raise HTTPException(status_code=404, detail="Figure image not found.")
    return FileResponse(figure_path)


@app.get("/api/papers/{paper_id}/ingestion-sections/{section_canonical}")
async def get_paper_ingestion_section_detail(
    paper_id: int,
    section_canonical: str,
    max_chars: int = 250000,
) -> Dict[str, Any]:
    if max_chars < 1000 or max_chars > 2_000_000:
        raise HTTPException(status_code=400, detail="max_chars must be between 1000 and 2000000.")

    target = str(section_canonical or "").strip().lower()
    if not target:
        raise HTTPException(status_code=400, detail="section_canonical is required.")

    paper = _get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, page_no, block_index, text, metadata
                FROM text_blocks
                WHERE paper_id=$1
                ORDER BY page_no ASC, block_index ASC
                """,
                paper_id,
            )
    except Exception as exc:
        logger.exception("Failed to load ingestion section detail for paper %s", paper_id)
        raise HTTPException(status_code=500, detail=str(exc))

    source_blocks: Dict[tuple[int, int, str], Dict[str, Any]] = {}
    chunk_ids: set[int] = set()
    section_titles: set[str] = set()
    section_source_counts: Dict[str, int] = {}

    for row in rows:
        metadata = _as_json_dict(row["metadata"])
        section_primary = str(metadata.get("section_primary") or "").strip().lower()
        section_all_raw = metadata.get("section_all")
        if not isinstance(section_all_raw, list):
            section_all_raw = [section_primary] if section_primary else []
        section_all = [str(item).strip().lower() for item in section_all_raw if str(item).strip()]
        if target in section_all or section_primary == target:
            chunk_ids.add(int(row["id"]))

        block_items = _as_json_list(metadata.get("blocks"))
        if not block_items:
            # Fallback for chunks without original source-block metadata.
            if target in section_all or section_primary == target:
                chunk_text = str(row["text"] or "").replace("\x00", "").strip()
                if chunk_text:
                    key = (int(row["page_no"]), int(row["block_index"]), chunk_text)
                    source_blocks.setdefault(
                        key,
                        {
                            "page_no": int(row["page_no"]),
                            "block_index": int(row["block_index"]),
                            "text": chunk_text,
                            "bbox": None,
                            "section_title": str(metadata.get("section_title") or ""),
                            "section_source": str(metadata.get("section_source") or "unknown"),
                            "section_confidence": metadata.get("section_confidence"),
                        },
                    )
            continue

        for block in block_items:
            if not isinstance(block, dict):
                continue
            block_text = str(block.get("text") or "").replace("\x00", "").strip()
            if not block_text:
                continue
            block_meta = block.get("metadata")
            block_meta = block_meta if isinstance(block_meta, dict) else {}
            block_canonical = str(block_meta.get("section_canonical") or "").strip().lower()
            if not block_canonical:
                block_canonical = section_primary
            if block_canonical != target:
                continue

            page_no = int(block.get("page_no") or row["page_no"])
            block_index = int(block.get("block_index") or 0)
            section_title = str(block_meta.get("section_title") or "").strip()
            section_source = str(
                block_meta.get("section_source")
                or metadata.get("section_source")
                or "unknown"
            ).strip() or "unknown"
            section_confidence = block_meta.get("section_confidence")
            block_bbox = _as_json_dict(block.get("bbox"))
            if not block_bbox:
                block_bbox = None

            key = (page_no, block_index, block_text)
            source_blocks.setdefault(
                key,
                {
                    "page_no": page_no,
                    "block_index": block_index,
                    "text": block_text,
                    "bbox": block_bbox,
                    "section_title": section_title,
                    "section_source": section_source,
                    "section_confidence": section_confidence,
                },
            )

            if section_title:
                section_titles.add(section_title)
            section_source_counts[section_source] = section_source_counts.get(section_source, 0) + 1

    ordered_blocks = sorted(
        source_blocks.values(),
        key=lambda item: (item["page_no"], item["block_index"]),
    )
    pages = sorted({item["page_no"] for item in ordered_blocks})
    full_text = "\n\n".join(item["text"] for item in ordered_blocks).strip()
    truncated = False
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars]
        truncated = True

    manifest = paper_figures.load_paper_figure_manifest(paper_id)
    all_images = manifest.get("images") or []
    section_images = [
        img for img in all_images
        if str(img.get("section_canonical") or "").strip().lower() == target
    ]
    if not section_images and pages:
        page_set = set(pages)
        section_images = [
            img for img in all_images
            if int(img.get("page_no") or 0) in page_set
        ]

    section_images = sorted(
        section_images,
        key=lambda item: (
            int(item.get("page_no") or 0),
            int(item.get("id") or 0),
        ),
    )

    return {
        "paper_id": paper_id,
        "paper_title": paper.get("title"),
        "section_canonical": target,
        "section_title_samples": sorted(section_titles)[:10],
        "pages": pages,
        "source_block_count": len(ordered_blocks),
        "chunk_count": len(chunk_ids),
        "full_text": full_text,
        "full_text_chars": len(full_text),
        "truncated": truncated,
        "section_source_counts": [
            {"source": source, "count": count}
            for source, count in sorted(
                section_source_counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ],
        "images": section_images,
    }


@app.get("/api/notes")
def list_notes(
    q: Optional[str] = None,
    search_type: Optional[str] = None,
    paper_ids: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """
    List all notes or search notes with query parameter.
    
    Query params:
        q: Optional search query
        search_type: "keyword", "embedding", or "hybrid" (defaults to "keyword")
        paper_ids: Comma-separated list of paper IDs to filter by
    """
    if q:
        # Search notes
        st = search_type or "keyword"
        if st not in ["keyword", "embedding", "hybrid"]:
            st = "keyword"
        
        paper_id_list = None
        if paper_ids:
            try:
                paper_id_list = [int(pid.strip()) for pid in paper_ids.split(",") if pid.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid paper_ids format")
        
        results = search_notes(q, search_type=st, paper_ids=paper_id_list, limit=100)
        notes: List[Dict[str, Any]] = []
        for row in results:
            note = dict(row)
            note["tags"] = _parse_tags(note.pop("tags_json", None))
            notes.append(note)
        return {"notes": notes}
    else:
        # Return all notes
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                       p.title AS paper_title
                FROM notes n
                LEFT JOIN papers p ON p.id = n.paper_id
                ORDER BY datetime(n.created_at) DESC, n.id DESC
                """
            ).fetchall()
        notes: List[Dict[str, Any]] = []
        for row in rows:
            note = dict(row)
            note["tags"] = _parse_tags(note.pop("tags_json", None))
            notes.append(note)
        return {"notes": notes}


@app.post("/api/notes", status_code=201)
def create_note(payload: NoteCreate) -> Dict[str, Dict]:
    tags_json = json.dumps(payload.tags or [], ensure_ascii=False) if payload.tags is not None else None
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notes (paper_id, title, body, tags_json, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (payload.paper_id, payload.title or "Untitled", payload.body, tags_json),
        )
        note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = conn.execute(
            """
            SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                   p.title AS paper_title
            FROM notes n
            LEFT JOIN papers p ON p.id = n.paper_id
            WHERE n.id=?
            """,
            (note_id,),
        ).fetchone()
    note = dict(row)
    note["tags"] = _parse_tags(note.pop("tags_json", None))
    return {"note": note}


@app.put("/api/notes/{note_id}")
def update_note(note_id: int, payload: NoteUpdate) -> Dict[str, Dict]:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, paper_id, title, body, tags_json FROM notes WHERE id=?",
            (note_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Note not found.")
        new_title = payload.title if payload.title is not None else existing["title"]
        new_body = payload.body if payload.body is not None else existing["body"]
        new_paper_id = payload.paper_id if payload.paper_id is not None else existing["paper_id"]
        new_tags_json = (
            json.dumps(payload.tags or [], ensure_ascii=False)
            if payload.tags is not None
            else existing["tags_json"]
        )
        conn.execute(
            "UPDATE notes SET paper_id=?, title=?, body=?, tags_json=? WHERE id=?",
            (new_paper_id, new_title, new_body, new_tags_json, note_id),
        )
        row = conn.execute(
            """
            SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                   p.title AS paper_title
            FROM notes n
            LEFT JOIN papers p ON p.id = n.paper_id
            WHERE n.id=?
            """,
            (note_id,),
        ).fetchone()
    note = dict(row)
    note["tags"] = _parse_tags(note.pop("tags_json", None))
    return {"note": note}


@app.delete("/api/notes/{note_id}", status_code=204, response_class=Response)
def remove_note(note_id: int) -> Response:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found.")
    return Response(status_code=204)


@app.get("/api/papers/{paper_id}/summaries")
def list_summaries(
    paper_id: int,
    q: Optional[str] = None,
    search_type: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """
    List all summaries for a paper or search summaries with query parameter.
    
    Query params:
        q: Optional search query
        search_type: "keyword", "embedding", or "hybrid" (defaults to "keyword")
    """
    if q:
        # Search summaries
        st = search_type or "keyword"
        if st not in ["keyword", "embedding", "hybrid"]:
            st = "keyword"
        
        results = search_summaries(q, search_type=st, paper_ids=[paper_id], limit=100)
        summaries: List[Dict[str, Any]] = []
        for row in results:
            summary = dict(row)
            summary["metadata"] = _parse_metadata(summary.pop("metadata_json", None))
            summary["is_edited"] = bool(summary.get("is_edited"))
            summaries.append(summary)
        return {"summaries": summaries}
    else:
        # Return all summaries for the paper
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, paper_id, title, content, agent, style, word_count, is_edited,
                       metadata_json, created_at, updated_at
                FROM summaries
                WHERE paper_id=?
                ORDER BY datetime(created_at) DESC, id DESC
                """,
                (paper_id,),
            ).fetchall()
        summaries: List[Dict[str, Any]] = []
        for row in rows:
            summary = dict(row)
            summary["metadata"] = _parse_metadata(summary.pop("metadata_json", None))
            summary["is_edited"] = bool(summary.get("is_edited"))
            summaries.append(summary)
        return {"summaries": summaries}


@app.post("/api/papers/{paper_id}/summaries", status_code=201)
def create_summary(paper_id: int, payload: SummaryCreate) -> Dict[str, Dict]:
    metadata_json = (
        json.dumps(payload.metadata, ensure_ascii=False)
        if payload.metadata is not None
        else None
    )
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Paper not found.")
        conn.execute(
            """
            INSERT INTO summaries (paper_id, title, content, agent, style, word_count, is_edited, metadata_json,
                                   created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                paper_id,
                payload.title,
                payload.content,
                payload.agent,
                payload.style,
                payload.word_count,
                1 if payload.is_edited else 0,
                metadata_json,
            ),
        )
        summary_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = conn.execute(
            """
            SELECT id, paper_id, title, content, agent, style, word_count, is_edited,
                   metadata_json, created_at, updated_at
            FROM summaries
            WHERE id=?
            """,
            (summary_id,),
        ).fetchone()
    summary = dict(row)
    summary["metadata"] = _parse_metadata(summary.pop("metadata_json", None))
    summary["is_edited"] = bool(summary.get("is_edited"))
    return {"summary": summary}


@app.put("/api/summaries/{summary_id}")
def update_summary_record(summary_id: int, payload: SummaryUpdate) -> Dict[str, Dict]:
    with get_conn() as conn:
        existing = conn.execute(
            """
            SELECT id, paper_id, title, content, agent, style, word_count, is_edited,
                   metadata_json, created_at, updated_at
            FROM summaries
            WHERE id=?
            """,
            (summary_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Summary not found.")
        new_title = payload.title if payload.title is not None else existing["title"]
        new_content = payload.content if payload.content is not None else existing["content"]
        new_agent = payload.agent if payload.agent is not None else existing["agent"]
        new_style = payload.style if payload.style is not None else existing["style"]
        new_word_count = (
            payload.word_count if payload.word_count is not None else existing["word_count"]
        )
        new_is_edited = (
            1 if payload.is_edited is True else 0 if payload.is_edited is False else existing["is_edited"]
        )
        new_metadata_json = (
            json.dumps(payload.metadata, ensure_ascii=False)
            if payload.metadata is not None
            else existing["metadata_json"]
        )
        conn.execute(
            """
            UPDATE summaries
            SET title=?, content=?, agent=?, style=?, word_count=?, is_edited=?, metadata_json=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                new_title,
                new_content,
                new_agent,
                new_style,
                new_word_count,
                new_is_edited,
                new_metadata_json,
                summary_id,
            ),
        )
        row = conn.execute(
            """
            SELECT id, paper_id, title, content, agent, style, word_count, is_edited,
                   metadata_json, created_at, updated_at
            FROM summaries
            WHERE id=?
            """,
            (summary_id,),
        ).fetchone()
    summary = dict(row)
    summary["metadata"] = _parse_metadata(summary.pop("metadata_json", None))
    summary["is_edited"] = bool(summary.get("is_edited"))
    return {"summary": summary}


@app.delete("/api/summaries/{summary_id}", status_code=204, response_class=Response)
def delete_summary_record(summary_id: int) -> Response:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM summaries WHERE id=?", (summary_id,))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Summary not found.")
    return Response(status_code=204)


@app.get("/api/question-sets")
def get_question_sets() -> Dict[str, List[Dict]]:
    return {"question_sets": list_question_sets()}


@app.get("/api/question-sets/{set_id}")
def get_question_set_detail(set_id: int) -> Dict[str, Any]:
    payload = get_question_set(set_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Question set not found.")
    return payload


@app.post("/api/question-sets", status_code=201)
def create_question_set_handler(payload: QuestionSetCreate) -> Dict[str, Any]:
    try:
        data = create_question_set(payload.prompt, [q.model_dump() for q in payload.questions])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return data


@app.put("/api/question-sets/{set_id}")
def update_question_set_handler(set_id: int, payload: QuestionSetUpdate) -> Dict[str, Any]:
    try:
        data = update_question_set(set_id, payload.prompt, [q.model_dump() for q in payload.questions])
    except ValueError as exc:
        detail = str(exc)
        code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail)
    return data


@app.delete("/api/question-sets/{set_id}", status_code=204, response_class=Response)
def delete_question_set_handler(set_id: int) -> Response:
    if not get_question_set(set_id):
        raise HTTPException(status_code=404, detail="Question set not found.")
    delete_question_set(set_id)
    return Response(status_code=204)


@app.post("/api/question-sets/generate", response_model=QuestionGenerationResponse)
async def generate_question_set_ai(payload: QuestionGenerationRequest) -> QuestionGenerationResponse:
    try:
        return await run_in_threadpool(generate_questions, payload)
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/question-sets/generate/stream")
async def generate_question_set_stream(payload: QuestionGenerationRequest):
    async def event_stream():
        try:
            async for event in stream_generate_questions(payload):
                yield f"data: {json.dumps(event)}\n\n"
        except QuestionGenerationError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/question-sets/context", response_model=QuestionContextUploadResponse)
async def upload_question_context(file: UploadFile = File(...)) -> QuestionContextUploadResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file was empty.")
    try:
        filename = file.filename or "upload"
        if not mcp_configured():
            context = await extract_context_from_upload(filename, contents)
            context_store.save_context(context)
            return context
        data_b64 = base64.b64encode(contents).decode("utf-8")
        try:
            payload = await call_mcp_tool_async(
                "upload_context",
                {
                    "filename": filename,
                    "data_b64": data_b64,
                },
            )
        except Exception as exc:
            logger.warning("MCP upload_context failed, falling back to local extraction: %s", exc)
            context = await extract_context_from_upload(filename, contents)
            context_store.save_context(context)
            return context
        context_data = (payload or {}).get("context")
        if not context_data:
            raise HTTPException(status_code=500, detail="MCP server did not return context metadata.")
        context = QuestionContextUploadResponse(**context_data)
        context_store.save_context(context)
        return context
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/question-sets/{set_id}/preview/insert", response_model=QuestionInsertionPreviewResponse)
async def preview_question_insertion(set_id: int, payload: QuestionInsertionRequest) -> QuestionInsertionPreviewResponse:
    question_set_payload = get_question_set(set_id)
    if not question_set_payload:
        raise HTTPException(status_code=404, detail="Question set not found.")
    try:
        preview_questions, merged_questions, insert_index = await run_in_threadpool(
            generate_insertion_preview,
            question_set_payload,
            payload,
        )
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return QuestionInsertionPreviewResponse(
        question_set=question_set_payload["question_set"],
        preview_questions=preview_questions,
        merged_questions=merged_questions,
        insert_index=insert_index,
    )


@app.post("/api/papers/download", status_code=201)
async def download_paper(payload: PaperDownloadRequest) -> Dict[str, PaperRecord]:
    source = payload.source.strip()
    if not source:
        raise HTTPException(status_code=400, detail="Enter a DOI, URL, or PDF source.")
    try:
        result = await add_paper(source, payload.source_url or source)
    except RuntimeError as exc:
        if _looks_like_url(source) and "Could not locate a PDF" in str(exc):
            result = await add_web_page(source, payload.source_url or source)
        else:
            raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET rag_status=?, rag_error=NULL, rag_updated_at=datetime('now') WHERE id=?",
            ("queued", result["paper_id"]),
        )
        conn.commit()
    paper = _get_paper(result["paper_id"])
    if not paper:
        raise HTTPException(status_code=500, detail="Downloaded paper could not be loaded.")
    return {"paper": PaperRecord.model_validate(paper)}


@app.delete("/api/papers/{paper_id}", status_code=204, response_class=Response)
def delete_paper_handler(paper_id: int) -> Response:
    paper = _get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    try:
        delete_paper_record(paper_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    path = paper.get("pdf_path")
    if path:
        pdf_path = Path(path)
        pdf_path.unlink(missing_ok=True)
    def _delete_pg_blocks() -> None:
        async def _run():
            try:
                from backend.rag.pgvector_store import PgVectorStore
                pool = await get_pg_pool()
                store = PgVectorStore(pool)
                await store.delete_paper_blocks(paper_id)
            finally:
                await close_pg_pool()
        try:
            asyncio.run(_run())
        except Exception:
            logger.exception("Failed to remove pgvector blocks for paper %s", paper_id)

    threading.Thread(target=_delete_pg_blocks, daemon=True).start()
    return Response(status_code=204)


@app.post("/api/papers/{paper_id}/chat")
async def paper_summary_chat(paper_id: int, payload: PaperChatRequest) -> Dict[str, Any]:
    if not payload.messages:
        raise HTTPException(status_code=400, detail="Provide at least one message.")
    try:
        data = await run_in_threadpool(
            summarize_paper_chat,
            paper_id,
            [m for m in payload.messages],
            payload.provider,
            payload.section_ids,
        )
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return data


@app.post("/api/question-sets/{set_id}/canvas")
def push_question_set_canvas(set_id: int, payload: CanvasPushRequest) -> Dict[str, Any]:
    data = get_question_set(set_id)
    if not data:
        raise HTTPException(status_code=404, detail="Question set not found.")
    try:
        result = push_question_set_to_canvas(set_id, data, payload)
    except CanvasPushError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return CanvasPushResponse(**result)


# Qwen tool endpoints

def _wrap_tool_call(fn, **kwargs) -> Dict[str, Any]:
    try:
        return fn(**kwargs)
    except Exception as exc:
        logger.exception("Tool execution failed")
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/tools/web-search")
def tool_web_search(payload: WebSearchRequest) -> Dict[str, Any]:
    return {"result": _wrap_tool_call(qwen_tools.web_search, query=payload.query, max_results=payload.max_results or 5)}


@app.post("/api/tools/news")
def tool_news(payload: NewsRequest) -> Dict[str, Any]:
    return {"result": _wrap_tool_call(qwen_tools.get_news, topic=payload.topic, limit=payload.limit or 10)}


@app.post("/api/tools/arxiv/search")
def tool_arxiv_search(payload: ArxivSearchRequest) -> Dict[str, Any]:
    return {"result": _wrap_tool_call(qwen_tools.arxiv_search, query=payload.query, max_results=payload.max_results or 5)}


@app.post("/api/tools/arxiv/download")
def tool_arxiv_download(payload: ArxivDownloadRequest) -> Dict[str, Any]:
    return {
        "result": _wrap_tool_call(
            qwen_tools.arxiv_download,
            arxiv_id=payload.arxiv_id,
            output_path=payload.output_path,
        )
    }


@app.post("/api/tools/pdf/summary")
def tool_pdf_summary(payload: PdfSummaryRequest) -> Dict[str, Any]:
    return {"result": _wrap_tool_call(qwen_tools.pdf_summary, pdf_path=payload.pdf_path)}


@app.post("/api/tools/youtube/search")
def tool_youtube_search(payload: YoutubeSearchRequest) -> Dict[str, Any]:
    return {
        "result": _wrap_tool_call(
            qwen_tools.youtube_search, query=payload.query, max_results=payload.max_results or 5
        )
    }


@app.post("/api/tools/youtube/download")
def tool_youtube_download(payload: YoutubeDownloadRequest) -> Dict[str, Any]:
    return {
        "result": _wrap_tool_call(
            qwen_tools.youtube_download,
            video_url=payload.video_url,
            output_path=payload.output_path,
        )
    }


@app.post("/api/agent/chat", response_model=AgentChatResponse)
def agent_chat(payload: AgentChatRequest) -> AgentChatResponse:
    try:
        convo = run_agent([m.model_dump() for m in payload.messages])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AgentChatResponse(messages=convo)


# RAG endpoints

@app.post("/api/rag/ingest", response_model=RAGIngestResponse)
async def rag_ingest(payload: RAGIngestRequest) -> RAGIngestResponse:
    """Ingest library documents into PostgreSQL (pgvector)."""
    chunk_size = payload.chunk_size or 1200
    chunk_overlap = payload.chunk_overlap or 200
    requested_ids = payload.paper_ids or []

    with get_conn() as conn:
        if requested_ids:
            placeholders = ",".join("?" for _ in requested_ids)
            rows = conn.execute(
                f"""
                SELECT id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at
                FROM papers
                WHERE id IN ({placeholders})
                """,
                tuple(requested_ids),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at
                FROM papers
                """
            ).fetchall()

    papers = [dict(row) for row in rows]
    if not papers:
        return RAGIngestResponse(
            success=False,
            message="No documents found for ingestion.",
            num_documents=0,
        )

    paper_ids = [p["id"] for p in papers]
    pdf_papers = [p for p in papers if p.get("pdf_path")]
    web_papers = [p for p in papers if not p.get("pdf_path")]
    pdf_paths = [p["pdf_path"] for p in pdf_papers if p.get("pdf_path")]
    metadata_by_path = {
        str(Path(p["pdf_path"]).expanduser().resolve()): {
            "paper_id": p["id"],
            "paper_title": p.get("title") or Path(p["pdf_path"]).stem,
        }
        for p in pdf_papers
        if p.get("pdf_path")
    }
    _set_rag_status(paper_ids, "processing", None)

    try:
        await _upsert_pg_papers(papers)
        pdf_result: Dict[str, Any] = {"papers_ingested": 0, "total_chunks": 0, "failed": []}
        if pdf_papers:
            pdf_ids = [p["id"] for p in pdf_papers]
            pdf_result = await ingest_pgvector.ingest_papers_from_db(
                paper_ids=pdf_ids,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        web_result = await _ingest_web_papers(web_papers)
        if os.getenv("ENABLE_IMAGE_INDEX", "true").lower() in {"1", "true", "yes"}:
            image_index_dir = os.getenv("IMAGE_INDEX_DIR", str(BACKEND_ROOT / "index_images"))
            figure_dir = os.getenv("FIGURE_OUTPUT_DIR", str(DATA_DIR / "figures"))
            try:
                image_index.build_image_index(pdf_paths, metadata_by_path, figure_dir, image_index_dir)
            except Exception as exc:
                logger.exception("Image indexing failed: %s", exc)

        failed: List[Dict[str, Any]] = []
        failed.extend(pdf_result.get("failed") or [])
        failed.extend(web_result.get("failed") or [])
        failed_ids = {f.get("paper_id") for f in failed if f.get("paper_id")}
        success_ids = [pid for pid in paper_ids if pid not in failed_ids]
        if success_ids:
            _set_rag_status(success_ids, "done", None)
        for f in failed:
            pid = f.get("paper_id")
            if pid is not None:
                _set_rag_status([pid], "error", str(f.get("error") or "Ingestion failed")[:500])

        papers_ingested = pdf_result.get("papers_ingested", 0) + web_result.get("papers_ingested", 0)
        message = f"Successfully ingested {papers_ingested} document(s) into pgvector."
        if failed:
            message = f"Ingested {papers_ingested} document(s); {len(failed)} failed."
        return RAGIngestResponse(
            success=len(failed) == 0,
            message=message,
            num_documents=papers_ingested,
            num_chunks=(pdf_result.get("total_chunks", 0) or 0) + (web_result.get("total_chunks", 0) or 0),
            index_dir=payload.index_dir or "pgvector",
        )
    except Exception as exc:
        logger.exception("RAG ingestion failed")
        _set_rag_status(paper_ids, "error", str(exc))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")


@app.get("/api/rag/status", response_model=RAGIndexStatusResponse)
async def rag_status(index_dir: Optional[str] = None) -> RAGIndexStatusResponse:
    """Check the status of the pgvector index."""
    try:
        status = await query_pgvector.check_index_status()
        return RAGIndexStatusResponse(
            exists=status.get("exists", False),
            message=status.get("message", ""),
            index_dir=index_dir or "pgvector",
        )
    except Exception as exc:
        logger.exception("Failed to check RAG index status")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/rag/query", response_model=RAGQueryResponse)
async def rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    """Query the RAG system with a question."""
    try:
        k = payload.k or 6
        headless = payload.headless if payload.headless is not None else False  # Default to False to show browser
        search_type = payload.search_type or "embedding"
        
        # Validate search_type
        if search_type not in ["keyword", "embedding", "hybrid"]:
            search_type = "embedding"

        alpha_raw = os.getenv("HYBRID_SEARCH_ALPHA", "0.5")
        try:
            alpha = float(alpha_raw)
        except ValueError:
            alpha = 0.5

        result = await query_pgvector.query_rag(
            payload.question,
            k=k,
            paper_ids=payload.paper_ids,
            provider=payload.provider,
            search_type=search_type,
            alpha=alpha,
            headless=headless,
        )

        # Convert context info to proper format
        from .schemas import RAGContextInfo
        context_info = [
            RAGContextInfo(**ctx) for ctx in result["context"]
        ]

        return RAGQueryResponse(
            question=result["question"],
            answer=result["answer"],
            context=context_info,
            num_sources=result["num_sources"]
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/papers/{paper_id}/rag-qa", response_model=List[RAGQnaRecord])
def list_rag_qna(paper_id: int) -> List[RAGQnaRecord]:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        rows = conn.execute(
            """
            SELECT id, paper_id, question, answer, sources_json, scope, provider, created_at
            FROM rag_qna
            WHERE paper_id=?
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (paper_id,),
        ).fetchall()
    return [
        RAGQnaRecord(
            id=row["id"],
            paper_id=row["paper_id"],
            question=row["question"],
            answer=row["answer"],
            sources=_parse_rag_sources(row["sources_json"]),
            scope=row["scope"],
            provider=row["provider"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@app.post("/api/papers/{paper_id}/rag-qa", response_model=RAGQnaRecord)
def create_rag_qna(paper_id: int, payload: RAGQnaCreateRequest) -> RAGQnaRecord:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        sources_json = json.dumps([s.model_dump() for s in payload.sources])
        cur = conn.execute(
            """
            INSERT INTO rag_qna(paper_id, question, answer, sources_json, scope, provider)
            VALUES(?,?,?,?,?,?)
            """,
            (
                paper_id,
                payload.question,
                payload.answer,
                sources_json,
                payload.scope,
                payload.provider,
            ),
        )
        conn.commit()
        row_id = cur.lastrowid
        row = conn.execute(
            """
            SELECT id, paper_id, question, answer, sources_json, scope, provider, created_at
            FROM rag_qna
            WHERE id=?
            """,
            (row_id,),
        ).fetchone()
    return RAGQnaRecord(
        id=row["id"],
        paper_id=row["paper_id"],
        question=row["question"],
        answer=row["answer"],
        sources=_parse_rag_sources(row["sources_json"]),
        scope=row["scope"],
        provider=row["provider"],
        created_at=row["created_at"],
    )


@app.delete("/api/papers/{paper_id}/rag-qa/{qa_id}")
def delete_rag_qna(paper_id: int, qa_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM rag_qna WHERE id=? AND paper_id=?",
            (qa_id, paper_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Q&A entry not found")
    return {"deleted": True}


@app.delete("/api/papers/{paper_id}/rag-qa")
def clear_rag_qna(paper_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Paper not found")
        conn.execute("DELETE FROM rag_qna WHERE paper_id=?", (paper_id,))
        conn.commit()
    return {"cleared": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8010, reload=True)
