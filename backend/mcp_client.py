from __future__ import annotations

import os
from typing import Any, Dict

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import StreamableHTTPError, streamablehttp_client
from mcp.types import CallToolResult, ContentBlock


LOCAL_MCP_SERVER_URL = os.getenv("LOCAL_MCP_SERVER_URL")


class MCPClientError(RuntimeError):
    """Raised when the MCP server call fails or returns an error."""


def _extract_text(blocks: list[ContentBlock]) -> str:
    parts = []
    for block in blocks or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def is_configured() -> bool:
    return bool(LOCAL_MCP_SERVER_URL)


def _format_result(name: str, result: CallToolResult) -> Dict[str, Any]:
    if result.isError:
        message = _extract_text(result.content)
        structured = result.structuredContent or {}
        detail = structured.get("error") if isinstance(structured, dict) else None
        raise MCPClientError(message or detail or f"MCP tool '{name}' returned an error.")
    structured = result.structuredContent or {}
    if not structured and result.content:
        structured = {"content": _extract_text(result.content)}
    return structured


async def _call_tool_async(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if not LOCAL_MCP_SERVER_URL:
        raise MCPClientError("LOCAL_MCP_SERVER_URL is not configured.")
    try:
        async with streamablehttp_client(url=LOCAL_MCP_SERVER_URL) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments or {})
    except StreamableHTTPError as exc:
        raise MCPClientError(str(exc)) from exc
    return _format_result(name, result)


async def call_tool_async(name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return await _call_tool_async(name, arguments or {})


def call_tool(name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Call a tool on the local MCP server from synchronous code."""
    return anyio.run(_call_tool_async, name, arguments or {})
