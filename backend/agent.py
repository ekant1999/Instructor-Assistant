from __future__ import annotations

import json
import os
import logging
from typing import List, Dict, Any

from pathlib import Path
import ollama
from backend.core.database import get_conn

from . import qwen_tools
from backend import context_store
from backend.core.library import add_local_pdf
from backend.services import summarize_paper_chat
from backend.schemas import PaperChatMessage
from backend.mcp_client import MCPClientError, call_tool as call_mcp_tool, is_configured as mcp_configured

# Define the function-calling tool schemas for the model
TOOL_DEFS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information using DuckDuckGo",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get latest news articles from Google News RSS feed",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "News topic to search"},
                    "limit": {
                        "type": "integer",
                        "description": "Max number of articles",
                        "default": 10,
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arxiv_search",
            "description": "Search for research papers on arXiv",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for arXiv"},
                    "max_results": {
                        "type": "integer",
                        "description": "Max number of papers",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arxiv_download",
            "description": "Download a PDF paper from arXiv by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "arxiv_id": {"type": "string", "description": "arXiv paper ID"},
                    "output_path": {
                        "type": "string",
                        "description": "Optional output path (relative to downloads dir)",
                    },
                },
                "required": ["arxiv_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Search for videos on YouTube",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Max number of videos",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_download",
            "description": "Download a YouTube video by URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_url": {"type": "string", "description": "YouTube video URL"},
                    "output_path": {
                        "type": "string",
                        "description": "Optional output path (relative to downloads dir)",
                    },
                },
                "required": ["video_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contexts",
            "description": "List uploaded PDF/PPTX contexts for question generation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_context",
            "description": "Read a slice of an uploaded context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context_id": {"type": "string", "description": "Context ID to read"},
                    "start": {"type": "integer", "description": "Start offset", "default": 0},
                    "length": {"type": "integer", "description": "Max characters to read", "default": 4000},
                },
                "required": ["context_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_question_set",
            "description": "Generate a question set from uploaded contexts using GPT-5 (OpenAI).",
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {"type": "string", "description": "Generation instructions"},
                    "question_count": {"type": "integer", "description": "Desired number of questions"},
                    "question_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred question types (mcq, short_answer, true_false, essay)",
                    },
                    "context_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific context IDs to use (optional)",
                    },
                },
                "required": ["instructions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "download_markdown",
            "description": "Return markdown content for download.",
            "parameters": {
                "type": "object",
                "properties": {
                    "markdown": {"type": "string", "description": "Markdown content"},
                    "filename": {"type": "string", "description": "Suggested filename"},
                },
                "required": ["markdown"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_md_editor",
            "description": "Ask the UI to open the Question Sets markdown editor.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_paper",
            "description": "Summarize a downloaded paper (defaults to most recent download).",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "integer",
                        "description": "Paper ID to summarize (optional).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note_entry",
            "description": "Save a note/summary to the Research Library.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "integer", "description": "Paper ID to attach the note to"},
                    "title": {"type": "string", "description": "Note title"},
                    "body": {"type": "string", "description": "Note body content"},
                },
                "required": ["paper_id", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_last_summary",
            "description": "Save the most recent summary produced by summarize_paper into Notes.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


SYSTEM_PROMPT = """You are a helpful AI assistant with access to various tools.

IMPORTANT TOOL USAGE RULES:

1. When user asks to "download" or "get" papers/videos, you MUST use the download tools (arxiv_download, youtube_download)

2. When user asks to "find" or "search", use search tools first (arxiv_search, youtube_search)

3. ALWAYS actually execute download tools - don't just provide links

4. After downloading, confirm the file location

Pick and call tools when they help answer the user's request. Prefer accurate retrieval over guessing.
If a task references the app's pages, you can mention the right section (Research Library, Notes, Question Sets) but tools are your primary way to fetch fresh info.
Never fabricate tool results—if a tool fails, explain briefly.
When the user asks for a paper summary:
- If no paper_id is provided and no recent download is known, ask which paper (by id/title) to summarize.
- If summarization fails, report the error instead of guessing.
After summarizing, ask if the user wants to save it to Notes; if yes, call save_last_summary (preferred) or save_note_entry with the summary.
When saving a summary/note, use the paper title as the note title (unless the user provides one) and tell the user it was saved to Notes (not the Research Library).
When asked to summarize a paper, use the summarize_paper tool (do not use pdf_summary).
When asked to generate questions:
- If context_ids are not provided but contexts exist, automatically use the most recently uploaded context(s).
- Call generate_question_set with the context text; don't ask the user to restate context_ids unless none are available."""

QWEN_MODEL = os.getenv("QWEN_AGENT_MODEL", "qwen2.5:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")  # optional override
_LAST_DOWNLOADED_PAPER_ID: int | None = None
_LAST_SUMMARY: Dict[str, Any] | None = None
logger = logging.getLogger(__name__)


def _chat_with_ollama(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model": QWEN_MODEL,
        "messages": messages,
        "tools": TOOL_DEFS,
    }
    if OLLAMA_HOST:
        kwargs["host"] = OLLAMA_HOST
    return ollama.chat(**kwargs)


def _save_note_direct(paper_id: int, title: str | None, body: str) -> Dict[str, Any]:
    with get_conn() as conn:
        paper_row = conn.execute(
            "SELECT title FROM papers WHERE id=?",
            (paper_id,),
        ).fetchone()
    paper_title = (paper_row["title"] if paper_row else None) or "Untitled paper"
    note_title = (title or paper_title or "Summary").strip() or paper_title
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notes (paper_id, title, body, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (paper_id, note_title, body),
        )
        nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = conn.execute(
            """
            SELECT n.id, n.paper_id, n.title, n.body, n.created_at,
                   p.title AS paper_title
            FROM notes n
            LEFT JOIN papers p ON p.id = n.paper_id
            WHERE n.id=?
            """,
            (nid,),
        ).fetchone()
    return {"note_id": nid, "note": dict(row) if row else None, "paper_title": paper_title}


def _save_last_summary() -> Dict[str, Any]:
    if not _LAST_SUMMARY:
        raise ValueError("No recent summary available to save. Summarize a paper first.")
    pid = _LAST_SUMMARY.get("paper_id")
    if not pid:
        raise ValueError("No paper_id found for the recent summary.")
    return _save_note_direct(
        int(pid),
        _LAST_SUMMARY.get("suggested_title") or _LAST_SUMMARY.get("paper_title"),
        _LAST_SUMMARY.get("summary") or "",
    )


def _summarize_paper(paper_id: int) -> Dict[str, Any]:
    logger.info("[agent] summarize_paper paper_id=%s", paper_id)
    data = summarize_paper_chat(
        paper_id,
        [PaperChatMessage(role="user", content="Summarize this paper.")],
    )
    if not data or not data.get("message"):
        raise ValueError("Summarization returned no content. Ensure the paper is indexed and try again.")
    summary_payload = {
        "paper_id": paper_id,
        "summary": data.get("message"),
        "suggested_title": data.get("suggested_title") or data.get("paper_title") or "Summary",
        "paper_title": data.get("paper_title"),
    }
    global _LAST_SUMMARY
    _LAST_SUMMARY = summary_payload
    return summary_payload


def _list_contexts() -> Dict[str, Any]:
    if mcp_configured():
        try:
            payload = call_mcp_tool("list_contexts", {})
            return payload or {}
        except MCPClientError as exc:
            logger.warning("MCP list_contexts failed, falling back to local context store: %s", exc)
    contexts = []
    for ctx in context_store.list_contexts():
        contexts.append(
            {
                "context_id": ctx.context_id,
                "filename": ctx.filename,
                "characters": ctx.characters,
                "preview": ctx.preview,
            }
        )
    return {"contexts": contexts}


def _read_context(context_id: str, start: int | None = None, length: int | None = None) -> Dict[str, Any]:
    if mcp_configured():
        try:
            return call_mcp_tool(
                "read_context",
                {"context_id": context_id, "start": start, "length": length},
            )
        except MCPClientError as exc:
            logger.warning("MCP read_context failed, falling back to local context store: %s", exc)
    if not context_id:
        return {"error": "missing_context_id"}
    ctx = context_store.get_context(context_id)
    if not ctx:
        return {"error": "not_found"}
    text = ctx.text or ""
    try:
        start_idx = max(0, int(start or 0))
    except (TypeError, ValueError):
        start_idx = 0
    try:
        requested_len = int(length) if length is not None else 4000
    except (TypeError, ValueError):
        requested_len = 4000
    requested_len = max(500, min(requested_len, 6000))
    snippet = text[start_idx : start_idx + requested_len]
    return {
        "context_id": context_id,
        "start": start_idx,
        "length": len(snippet),
        "has_more": start_idx + len(snippet) < len(text),
        "content": snippet,
    }


def _combine_contexts_text(context_ids: List[str] | None, max_chars: int = 60000) -> str:
    ctxs = _list_contexts().get("contexts") or []
    selected = ctxs if not context_ids else [c for c in ctxs if c.get("context_id") in context_ids]
    parts: List[str] = []
    remaining = max_chars
    for ctx in selected:
        cid = ctx.get("context_id")
        if not cid or remaining <= 0:
            continue
        chunk = _read_context(cid, 0, min(4000, remaining)).get("content") or ""
        if not chunk:
            continue
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
        parts.append(f"[{ctx.get('filename')}] {chunk}")
        remaining -= len(chunk)
    return "\n\n".join(parts).strip()


def _generate_question_set_from_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import QuestionGenerationRequest, generate_questions

    raw_instructions = payload.get("instructions") or ""
    question_count = payload.get("question_count")
    question_types = payload.get("question_types")
    context_ids = payload.get("context_ids")
    context_text = _combine_contexts_text(context_ids or None)
    if not context_text:
        # Fallback: use all available contexts if none were provided explicitly
        context_text = _combine_contexts_text(None)
    if not context_text:
        raise ValueError("No context available. Upload a PDF/PPTX first.")
    instructions = raw_instructions.strip()
    if len(instructions) < 5:
        # Build a minimal default prompt if counts/types are provided; otherwise, ask user for a prompt.
        parts = []
        if question_count:
            parts.append(f"Generate {question_count} questions")
        if question_types:
            parts.append(f"Types: {', '.join(question_types)}")
        default_instr = " ".join(parts).strip()
        if default_instr:
            instructions = default_instr + " grounded in the uploaded documents."
        else:
            raise ValueError("Provide instructions (at least 5 characters) for question generation.")
    req = QuestionGenerationRequest(
        instructions=instructions,
        context=context_text,
        question_count=question_count,
        question_types=question_types,
        provider="openai",
    )
    result = generate_questions(req)
    return {
        "questions": [q.model_dump() for q in result.questions],
        "markdown": result.markdown,
        "raw_response": result.raw_response,
        "action": "open_md_editor",
        "filename": "question-set.md",
    }


def run_agent(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Run an agent loop with function calling via Ollama (Qwen).
    Accepts messages with role user/assistant/tool.
    Returns the expanded conversation (excluding the initial system prompt).
    """
    latest_context_ids: List[str] = []
    last_user_text = ""
    saved_note_this_turn = False
    for m in messages:
        if m.get("role") == "tool" and m.get("name") == "context_hint":
            try:
                payload = json.loads(m.get("content") or "{}")
                ids = payload.get("context_ids") if isinstance(payload, dict) else None
                if isinstance(ids, list):
                    latest_context_ids = [str(i) for i in ids if isinstance(i, str)]
            except Exception:
                continue
        if m.get("role") == "user":
            last_user_text = m.get("content") or ""
    global _LAST_DOWNLOADED_PAPER_ID
    convo: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        entry: Dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
        if m["role"] == "tool" and m.get("name"):
            entry["name"] = m["name"]
        convo.append(entry)

    max_iters = 5
    for _ in range(max_iters):
        resp = _chat_with_ollama(convo)
        message = resp["message"]
        tool_calls = message.get("tool_calls") or []

        # If no tool calls, finalize
        if not tool_calls:
            convo.append({"role": "assistant", "content": message.get("content", "")})
            break

        # Append assistant stub with tool calls (for traceability)
        convo.append(
            {
                "role": "assistant",
                "content": message.get("content", "") or "",
                "tool_calls": tool_calls,
            }
        )

        # Execute each tool call and feed back results
        for call in tool_calls:
            func = call.get("function", {})
            name = func.get("name")
            raw_args = func.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            try:
                result = None
                if name in {
                    "web_search",
                    "get_news",
                    "arxiv_search",
                    "arxiv_download",
                    "youtube_search",
                    "youtube_download",
                }:
                    result = qwen_tools.execute_tool(name or "", **(args or {}))
                elif name == "summarize_paper":
                    pid = args.get("paper_id") if isinstance(args, dict) else None
                    target_id = int(pid) if pid is not None else (_LAST_DOWNLOADED_PAPER_ID or 0)
                    if not target_id:
                        raise ValueError("No paper_id provided and no recent download available. Download a paper first or specify paper_id.")
                    result = _summarize_paper(target_id)
                elif name == "save_note_entry":
                    pid = args.get("paper_id") if isinstance(args, dict) else None
                    if pid is None:
                        raise ValueError("paper_id is required.")
                    result = _save_note_direct(int(pid), args.get("title"), args.get("body") or "")
                    saved_note_this_turn = True
                elif name == "save_last_summary":
                    result = _save_last_summary()
                    saved_note_this_turn = True
                elif name == "list_contexts":
                    result = _list_contexts()
                elif name == "read_context":
                    result = _read_context(
                        args.get("context_id"),
                        args.get("start"),
                        args.get("length"),
                    )
                elif name == "generate_question_set":
                    payload_args = args or {}
                    if not payload_args.get("context_ids") and latest_context_ids:
                        payload_args["context_ids"] = latest_context_ids
                    result = _generate_question_set_from_context(payload_args)
                elif name == "download_markdown":
                    md = args.get("markdown") if isinstance(args, dict) else None
                    fname = args.get("filename") if isinstance(args, dict) else None
                    if not md:
                        raise ValueError("No markdown content provided.")
                    result = {"markdown": md, "filename": fname or "question-set.md", "download": True}
                elif name == "navigate_md_editor":
                    result = {"action": "open_md_editor"}
                else:
                    raise ValueError(f"Unknown tool: {name}")

                if name == "arxiv_download" and isinstance(result, dict) and result.get("file_path"):
                    try:
                        ingest = add_local_pdf(
                            result.get("title"),
                            Path(result["file_path"]),
                            result.get("pdf_url") or result.get("arxiv_id"),
                        )
                        result["paper_id"] = ingest["paper_id"]
                        _LAST_DOWNLOADED_PAPER_ID = ingest["paper_id"]
                    except Exception as ingest_exc:
                        result["ingest_error"] = f"Failed to add to library: {ingest_exc}"
                result_text = json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as exc:  # pragma: no cover - best-effort guard
                logger.exception("Tool '%s' failed", name)
                result_text = f"Tool '{name}' failed: {exc}"

            convo.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "content": result_text,
                }
            )

    # Heuristic fallback: if user asked to save/add summary and no tool call happened, auto-save the last summary.
    if last_user_text and not saved_note_this_turn:
        lt = last_user_text.lower()
        if ("save" in lt or "add" in lt) and ("note" in lt or "notes" in lt) and _LAST_SUMMARY:
            try:
                saved = _save_last_summary()
                convo.append(
                    {
                        "role": "tool",
                        "name": "save_last_summary",
                        "content": json.dumps(saved, ensure_ascii=False, indent=2),
                    }
                )
                note_title = (saved.get("note") or {}).get("title") if isinstance(saved, dict) else None
                convo.append(
                    {
                        "role": "assistant",
                        "content": f"Saved the most recent summary to Notes as '{note_title or (_LAST_SUMMARY.get('paper_title') or 'Summary')}'.",
                    }
                )
            except Exception as exc:
                convo.append(
                    {
                        "role": "assistant",
                        "content": f"Could not save the summary to Notes: {exc}",
                    }
                )
    # Drop system prompt before returning
    return [m for m in convo if m.get("role") != "system"]
