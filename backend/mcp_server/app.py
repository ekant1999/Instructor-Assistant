from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

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
from backend.core.library_tools import (
    find_library_papers,
    get_library_excerpt as get_library_excerpt_payload,
    get_library_figure as get_library_figure_payload,
    get_library_pdf as get_library_pdf_payload,
    get_library_section as get_library_section_payload,
    list_library_figures as list_library_figures_payload,
    list_library_sections as list_library_sections_payload,
    load_library_paper_context as load_library_paper_context_payload,
)
from backend import context_store, services
from backend.schemas import QuestionGenerationRequest
from backend.services import QuestionGenerationError


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

mcp = FastMCP(name="instructor-assistant-local")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

LibrarySearchMode = Literal["hybrid", "keyword", "semantic"]
DeliveryMode = Literal["reference", "base64"]


def _result(
    message: str,
    structured: Optional[Dict[str, Any]] = None,
) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=message)],
        structuredContent=structured or {},
    )


def _truncate_for_log(value: Any, *, max_chars: int = 240, max_items: int = 5) -> Any:
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + "...[truncated]"
    if isinstance(value, list):
        preview = [_truncate_for_log(item, max_chars=max_chars, max_items=max_items) for item in value[:max_items]]
        if len(value) > max_items:
            preview.append(f"...[{len(value) - max_items} more item(s)]")
        return preview
    if isinstance(value, dict):
        return {
            str(key): _truncate_for_log(val, max_chars=max_chars, max_items=max_items)
            for key, val in list(value.items())[:20]
        }
    return value


def _log_tool_response(tool_name: str, structured: Optional[Dict[str, Any]]) -> None:
    if structured is None:
        logger.info("MCP tool result: %s -> <no structured content>", tool_name)
        return
    logger.info(
        "MCP tool result: %s -> %s",
        tool_name,
        json.dumps(_truncate_for_log(structured), ensure_ascii=False),
    )


def _normalize_library_search_type(search_type: Optional[LibrarySearchMode]) -> str:
    mode = str(search_type or "hybrid").strip().lower()
    if mode == "semantic":
        return "embedding"
    if mode in {"hybrid", "keyword", "embedding"}:
        return mode
    return "hybrid"


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


@mcp.tool("find_library_paper")
def find_library_paper_tool(
    query: str,
    limit: Optional[int] = None,
    search_type: LibrarySearchMode = "hybrid",
) -> CallToolResult:
    """
    Find research-library papers by title/content query.

    Args:
        query: Required paper lookup string. This can be a title fragment, keyword phrase, or numeric paper id.
        limit: Optional maximum number of papers to return. Clamped to 1..20.
        search_type: Retrieval mode for the lookup stage.
            - `hybrid`: combine keyword and semantic retrieval. Best default.
            - `keyword`: lexical lookup only.
            - `semantic`: vector/embedding retrieval only.

    Returns:
        Matching paper candidates with `paper_id`, title, source URL, availability flags, and PDF reference.
    """
    logger.info(
        "MCP tool called: find_library_paper query=%r limit=%s search_type=%s",
        query,
        limit,
        search_type,
    )
    if not str(query or "").strip():
        return _result("query is required.", {"error": "missing_query"})
    try:
        papers = find_library_papers(
            query,
            limit=max(1, min(int(limit or 5), 20)),
            search_type=_normalize_library_search_type(search_type),
        )
    except Exception as exc:
        return _result(f"Library paper lookup failed: {exc}", {"error": "lookup_failed"})
    structured = {"query": query, "papers": papers}
    _log_tool_response("find_library_paper", structured)
    return _result(
        f"Found {len(papers)} matching paper(s).",
        structured,
    )


@mcp.tool("get_library_pdf")
def get_library_pdf_tool(
    paper_id: int,
    delivery: DeliveryMode = "reference",
    max_inline_bytes: Optional[int] = None,
) -> CallToolResult:
    """
    Resolve a library paper PDF as either a fetchable reference or inline base64 bytes.

    Args:
        paper_id: Target library paper id.
        delivery: Output mode.
            - `reference`: return an API reference payload. Preferred default for most tool use.
            - `base64`: return the actual PDF bytes inline as base64.
        max_inline_bytes: Maximum allowed inline payload size when `delivery='base64'`.
            Ignored in `reference` mode and clamped to 1 KiB..25 MB.

    Returns:
        A structured PDF payload with metadata plus either a backend reference or inline bytes.
    """
    logger.info(
        "MCP tool called: get_library_pdf paper_id=%s delivery=%s max_inline_bytes=%s",
        paper_id,
        delivery,
        max_inline_bytes,
    )
    try:
        payload = get_library_pdf_payload(
            int(paper_id),
            delivery=str(delivery or "reference").strip().lower(),
            max_inline_bytes=max(1024, min(int(max_inline_bytes or 5_242_880), 25_000_000)),
        )
    except Exception as exc:
        return _result(f"Failed to load library PDF: {exc}", {"error": "pdf_unavailable"})
    _log_tool_response("get_library_pdf", {"paper": payload})
    return _result(
        f"Resolved PDF for paper {paper_id}.",
        {"paper": payload},
    )


@mcp.tool("get_library_excerpt")
def get_library_excerpt_tool(
    paper_id: int,
    query: Optional[str] = None,
    page_no: Optional[int] = None,
    section_id: Optional[int] = None,
    max_chars: Optional[int] = None,
    search_type: LibrarySearchMode = "hybrid",
    limit: Optional[int] = None,
) -> CallToolResult:
    """
    Return a targeted text excerpt from a library paper.

    Provide exactly one selector:
    - `query` to retrieve the best localized excerpt for a search phrase
    - `page_no` to return text from a specific page
    - `section_id` to return text for a specific section row

    Args:
        paper_id: Target library paper id.
        query: Search phrase used to localize a relevant excerpt.
        page_no: Specific page number to read directly.
        section_id: Specific section id to read directly.
        max_chars: Maximum number of characters to return. Clamped to 500..20,000.
        search_type: Retrieval mode used only when `query` is provided.
            - `hybrid`: combine keyword and semantic retrieval. Best default.
            - `keyword`: lexical retrieval only.
            - `semantic`: vector/embedding retrieval only.
        limit: Maximum number of candidate hits to include in the response.

    Returns:
        A structured excerpt payload containing the top excerpt plus candidate hits when query mode is used.
    """
    logger.info(
        "MCP tool called: get_library_excerpt paper_id=%s query=%r page_no=%s section_id=%s max_chars=%s search_type=%s limit=%s",
        paper_id,
        query,
        page_no,
        section_id,
        max_chars,
        search_type,
        limit,
    )
    try:
        payload = get_library_excerpt_payload(
            int(paper_id),
            query=query,
            page_no=int(page_no) if page_no is not None else None,
            section_id=int(section_id) if section_id is not None else None,
            max_chars=max(500, min(int(max_chars or 4000), 20000)),
            search_type=_normalize_library_search_type(search_type),
            limit=max(1, min(int(limit or 5), 10)),
        )
    except Exception as exc:
        return _result(f"Failed to load library excerpt: {exc}", {"error": "excerpt_unavailable"})

    excerpt = payload.get("excerpt")
    _log_tool_response("get_library_excerpt", payload)
    if excerpt:
        page_label = excerpt.get("page_no")
        return _result(
            f"Returned library excerpt from page {page_label}.",
            payload,
        )
    return _result("No excerpt matched the request.", payload)


@mcp.tool("list_library_sections")
def list_library_sections_tool(paper_id: int) -> CallToolResult:
    """
    List canonical ingestion sections available for a library paper.

    Args:
        paper_id: Target library paper id.

    Returns:
        Section metadata such as canonical names, page coverage, source, and confidence.
    """
    logger.info("MCP tool called: list_library_sections paper_id=%s", paper_id)
    try:
        payload = list_library_sections_payload(int(paper_id))
    except Exception as exc:
        return _result(f"Failed to list library sections: {exc}", {"error": "section_list_failed"})
    _log_tool_response("list_library_sections", payload)
    return _result(
        f"Found {payload.get('section_count', 0)} section(s) for paper {paper_id}.",
        payload,
    )


@mcp.tool("get_library_section")
def get_library_section_tool(
    paper_id: int,
    section_canonical: str,
    max_chars: Optional[int] = None,
) -> CallToolResult:
    """
    Return a full canonical section from a library paper.

    Args:
        paper_id: Target library paper id.
        section_canonical: Canonical section name from `list_library_sections`.
        max_chars: Maximum section text size to return. Clamped to 1,000..250,000.

    Returns:
        Section text, page coverage, and associated figures, equations, and tables for that section.
    """
    logger.info(
        "MCP tool called: get_library_section paper_id=%s section_canonical=%r max_chars=%s",
        paper_id,
        section_canonical,
        max_chars,
    )
    if not str(section_canonical or "").strip():
        return _result("section_canonical is required.", {"error": "missing_section"})
    try:
        payload = get_library_section_payload(
            int(paper_id),
            section_canonical,
            max_chars=max(1000, min(int(max_chars or 60000), 250000)),
        )
    except Exception as exc:
        return _result(f"Failed to load library section: {exc}", {"error": "section_unavailable"})
    _log_tool_response("get_library_section", payload)
    return _result(
        f"Returned section '{section_canonical}' for paper {paper_id}.",
        payload,
    )


@mcp.tool("list_library_figures")
def list_library_figures_tool(
    paper_id: int,
    section_canonical: Optional[str] = None,
    page_no: Optional[int] = None,
    limit: Optional[int] = None,
) -> CallToolResult:
    """
    List extracted figures for a library paper.

    Args:
        paper_id: Target library paper id.
        section_canonical: Optional canonical section filter.
        page_no: Optional page filter.
        limit: Maximum number of figures to return. Clamped to 1..100.

    Returns:
        Figure metadata with page, section, caption, bbox, and image references.
    """
    logger.info(
        "MCP tool called: list_library_figures paper_id=%s section_canonical=%r page_no=%s limit=%s",
        paper_id,
        section_canonical,
        page_no,
        limit,
    )
    try:
        payload = list_library_figures_payload(
            int(paper_id),
            section_canonical=section_canonical,
            page_no=int(page_no) if page_no is not None else None,
            limit=max(1, min(int(limit or 20), 100)),
        )
    except Exception as exc:
        return _result(f"Failed to list library figures: {exc}", {"error": "figure_list_failed"})
    _log_tool_response("list_library_figures", payload)
    return _result(
        f"Found {payload.get('figure_count', 0)} figure(s) for paper {paper_id}.",
        payload,
    )


@mcp.tool("get_library_figure")
def get_library_figure_tool(
    paper_id: int,
    figure_name: str,
    delivery: DeliveryMode = "reference",
    max_inline_bytes: Optional[int] = None,
) -> CallToolResult:
    """
    Resolve an extracted paper figure as either a fetchable reference or inline base64 bytes.

    Args:
        paper_id: Target library paper id.
        figure_name: Exact figure file name from `list_library_figures`.
        delivery: Output mode.
            - `reference`: return an API reference payload. Preferred default.
            - `base64`: return the actual image bytes inline as base64.
        max_inline_bytes: Maximum allowed inline payload size when `delivery='base64'`.
            Ignored in `reference` mode and clamped to 1 KiB..25 MB.

    Returns:
        Figure metadata plus either a backend reference or inline bytes.
    """
    logger.info(
        "MCP tool called: get_library_figure paper_id=%s figure_name=%r delivery=%s max_inline_bytes=%s",
        paper_id,
        figure_name,
        delivery,
        max_inline_bytes,
    )
    if not str(figure_name or "").strip():
        return _result("figure_name is required.", {"error": "missing_figure_name"})
    try:
        payload = get_library_figure_payload(
            int(paper_id),
            figure_name,
            delivery=str(delivery or "reference").strip().lower(),
            max_inline_bytes=max(1024, min(int(max_inline_bytes or 5_242_880), 25_000_000)),
        )
    except Exception as exc:
        return _result(f"Failed to load library figure: {exc}", {"error": "figure_unavailable"})
    _log_tool_response("get_library_figure", payload)
    return _result(
        f"Resolved figure '{figure_name}' for paper {paper_id}.",
        payload,
    )


@mcp.tool("load_library_paper_context")
def load_library_paper_context_tool(
    paper_id: int,
    section_canonical: Optional[str] = None,
    max_chars: Optional[int] = None,
) -> CallToolResult:
    """
    Load a library paper, or one named section, into the MCP context store for incremental reading.

    Args:
        paper_id: Target library paper id.
        section_canonical: Optional canonical section name. If omitted, the full paper text is loaded.
        max_chars: Maximum amount of text to load into the context store. Clamped to 1,000..250,000.

    Returns:
        A normal MCP context payload containing `context_id`, preview text, and total character count.
    """
    logger.info(
        "MCP tool called: load_library_paper_context paper_id=%s section_canonical=%r max_chars=%s",
        paper_id,
        section_canonical,
        max_chars,
    )
    try:
        ctx = load_library_paper_context_payload(
            int(paper_id),
            section_canonical=section_canonical,
            max_chars=max(1000, min(int(max_chars or 60000), 250000)),
        )
    except Exception as exc:
        return _result(f"Failed to load library paper context: {exc}", {"error": "context_load_failed"})

    context_store.save_context(ctx)
    structured = {"context": ctx.model_dump()}
    _log_tool_response("load_library_paper_context", structured)
    if section_canonical:
        message = f"Loaded section '{section_canonical}' from paper {paper_id} into context store."
    else:
        message = f"Loaded paper {paper_id} into context store."
    return _result(message, structured)


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
