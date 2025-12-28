from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

from backend.core.questions import (
    create_question_set,
    delete_question_set,
    get_question_set,
    list_question_sets,
    update_question_set,
)
from backend import context_store, services
from backend.schemas import QuestionGenerationRequest
from backend.services import QuestionGenerationError


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

mcp = FastMCP(name="instructor-assistant-local")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


def _result(
    message: str,
    structured: Optional[Dict[str, Any]] = None,
) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        structuredContent=structured or {},
    )


def _context_payload(include_text: bool = False) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for ctx in context_store.list_contexts():
        data = {
            "context_id": ctx.context_id,
            "filename": ctx.filename,
            "characters": ctx.characters,
            "preview": ctx.preview,
        }
        if include_text:
            data["text"] = ctx.text
        payload.append(data)
    return payload


def _question_set_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "question_set": payload.get("question_set"),
        "questions": payload.get("questions"),
    }


@mcp.tool("upload_context")
async def upload_context(filename: str, data_b64: str) -> CallToolResult:
    logger.info("MCP tool called: upload_context (%s)", filename or "upload")
    """
    Accepts a base64-encoded PDF/PPT/PPTX file, extracts text, saves it to the context store,
    and returns the resulting context metadata.
    """
    if not data_b64:
        return _result("data_b64 is required.", {"error": "missing_data"})
    try:
        data = base64.b64decode(data_b64)
    except Exception as exc:
        return _result(f"Invalid base64 payload: {exc}", {"error": "invalid_base64"})

    try:
        ctx = await services.extract_context_from_upload(filename or "upload", data)
    except QuestionGenerationError as exc:
        return _result(str(exc), {"error": "extract_failed"})
    context_store.save_context(ctx)
    return _result("Context uploaded.", {"context": ctx.model_dump()})


@mcp.tool("list_contexts")
def list_contexts() -> CallToolResult:
    logger.info("MCP tool called: list_contexts")
    """
    Lists all available contexts and their metadata.
    """
    return _result(
        f"{len(context_store.list_contexts())} context(s) available.",
        {"contexts": _context_payload()},
    )


@mcp.tool("read_context")
def read_context(context_id: str, start: Optional[int] = None, length: Optional[int] = None) -> CallToolResult:
    logger.info("MCP tool called: read_context (%s)", context_id)
    """
    Returns a window of text from the specified context_id.
    """
    if not context_id:
        return _result("context_id is required.", {"error": "missing_context_id"})
    ctx = context_store.get_context(context_id)
    if not ctx:
        return _result(f"Context '{context_id}' not found.", {"error": "not_found"})
    try:
        start_idx = max(0, int(start or 0))
    except (TypeError, ValueError):
        start_idx = 0
    try:
        requested_len = int(length) if length is not None else 4000
    except (TypeError, ValueError):
        requested_len = 4000
    requested_len = max(500, min(requested_len, 6000))
    text = ctx.text or ""
    snippet = text[start_idx : start_idx + requested_len]
    payload = {
        "context_id": context_id,
        "start": start_idx,
        "length": len(snippet),
        "has_more": start_idx + len(snippet) < len(text),
        "content": snippet,
    }
    return _result("Context slice returned.", payload)


@mcp.tool("delete_context")
def delete_context(context_id: str) -> CallToolResult:
    logger.info("MCP tool called: delete_context (%s)", context_id)
    """
    Removes a context from the store.
    """
    if not context_id:
        return _result("context_id is required.", {"error": "missing_context_id"})
    context_store.clear_context(context_id)
    return _result(f"Context '{context_id}' removed.", {"context_id": context_id})


def _combine_contexts(context_ids: Optional[List[str]]) -> Optional[str]:
    selected: List[str] = []
    contexts = context_store.list_contexts()
    id_set = set(context_ids) if context_ids else None
    for ctx in contexts:
        if id_set is None or ctx.context_id in id_set:
            if ctx.text:
                selected.append(ctx.text)
    combined = "\n\n".join(selected).strip()
    return combined or None


@mcp.tool("generate_question_set")
def generate_question_set(
    instructions: str,
    context_ids: Optional[List[str]] = None,
    provider: Optional[str] = None,
    question_count: Optional[int] = None,
    question_types: Optional[List[str]] = None,
) -> CallToolResult:
    logger.info("MCP tool called: generate_question_set")
    """
    Generates questions using the shared question-generation pipeline.
    """
    context_text = _combine_contexts(context_ids)
    payload = {
        "instructions": instructions,
        "context": context_text,
        "provider": provider,
        "question_count": question_count,
        "question_types": question_types,
    }
    try:
        request = QuestionGenerationRequest(**{k: v for k, v in payload.items() if v is not None})
    except Exception as exc:
        return _result(f"Invalid request: {exc}", {"error": "invalid_request"})
    try:
        result = services.generate_questions(request)
    except QuestionGenerationError as exc:
        return _result(str(exc), {"error": "generation_failed"})
    structured = {
        "questions": [q.model_dump() for q in result.questions],
        "markdown": result.markdown,
        "raw_response": result.raw_response,
    }
    msg = f"Generated {len(structured['questions'])} question(s)."
    return _result(msg, structured)


@mcp.tool("extract_questions_and_answers")
def extract_questions_and_answers() -> CallToolResult:
    logger.info("MCP tool called: extract_questions_and_answers (unsupported)")
    return _result(
        "extract_questions_and_answers is not available. Use list_contexts/read_context and then return your final JSON.",
        {"error": "unsupported_tool"},
    )


@mcp.tool("list_question_sets")
def list_question_sets_tool() -> CallToolResult:
    rows = list_question_sets()
    return _result(f"Found {len(rows)} question set(s).", {"question_sets": rows})


@mcp.tool("get_question_set")
def get_question_set_tool(set_id: int) -> CallToolResult:
    payload = get_question_set(int(set_id))
    if not payload:
        return _result(f"Question set {set_id} not found.", {"error": "not_found"})
    return _result("Loaded question set.", _question_set_payload(payload))


@mcp.tool("save_question_set")
def save_question_set_tool(prompt: str, items: List[Dict[str, Any]]) -> CallToolResult:
    if not items:
        return _result("Provide at least one question.", {"error": "no_questions"})
    try:
        payload = create_question_set(prompt, items)
    except ValueError as exc:
        return _result(str(exc), {"error": "invalid_request"})
    structured = _question_set_payload(payload)
    count = len(structured.get("questions") or [])
    return _result(f"Saved {count} question(s).", structured)


@mcp.tool("update_question_set")
def update_question_set_tool(set_id: int, items: List[Dict[str, Any]], prompt: Optional[str] = None) -> CallToolResult:
    if not items:
        return _result("Provide at least one question.", {"error": "no_questions"})
    try:
        payload = update_question_set(int(set_id), prompt, items)
    except ValueError as exc:
        return _result(str(exc), {"error": "invalid_request"})
    structured = _question_set_payload(payload)
    count = len(structured.get("questions") or [])
    return _result(f"Updated {count} question(s).", structured)


@mcp.tool("delete_question_set")
def delete_question_set_tool(set_id: int) -> CallToolResult:
    delete_question_set(int(set_id))
    return _result(f"Deleted question set {set_id}.", {"set_id": set_id})


def run_server() -> None:
    try:
        mcp.run(transport="streamable-http", path="/mcp", stateless_http=True)
        return
    except TypeError:
        try:
            mcp.run(transport="streamable-http", path="/mcp")
            return
        except TypeError:
            mcp.run(transport="streamable-http")


if __name__ == "__main__":
    run_server()
