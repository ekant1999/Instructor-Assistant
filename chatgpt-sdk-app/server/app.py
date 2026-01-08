from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import base64
import json
import re
import secrets
from typing import Any, Dict, Optional, Tuple, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context
from mcp.types import (
    CallToolResult,
    Resource,
    TextContent,
    ReadResourceRequest,
    ReadResourceResult,
    ServerResult,
    TextResourceContents,
    BlobResourceContents,
)
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from server.db import init_db, get_conn
from server.tools.render_library import render_library_structured
from server.tools.add_paper import add_paper as add_paper_impl
from server.tools.index_paper import index_paper as index_paper_impl
from server.tools.get_paper_chunk import get_paper_chunk as get_paper_chunk_impl
from server.tools.save_note import save_note as save_note_impl
from server.question_sets import (
    create_question_set,
    delete_question_set,
    get_question_set,
    list_question_sets,
)


DIST_DIR = (Path(__file__).parent.parent / "web" / "dist")

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _read_first(globs: list[str]) -> str:
    for pat in globs:
        for p in DIST_DIR.glob(pat):
            return p.read_text(encoding="utf-8")
    return ""


def _find_first(globs: list[str]) -> Path | None:
    for pat in globs:
        for p in DIST_DIR.glob(pat):
            return p
    return None


fixed = DIST_DIR / "widget.js"
if fixed.exists():
    WIDGET_JS = fixed.read_text(encoding="utf-8")
else:
    alt = DIST_DIR / "widget"
    if alt.exists():
        WIDGET_JS = alt.read_text(encoding="utf-8")
    else:
        WIDGET_JS = _read_first(["*.js", "assets/*.js"]) or ""
        if not WIDGET_JS:
            print("[WARN] No web/dist/widget.js found. Run: cd web && npm i && npm run build")

WIDGET_CSS = _read_first(["*.css", "assets/*.css"])
WIDGET_JS_PATH = fixed if fixed.exists() else _find_first(["*.js", "assets/*.js"])
WIDGET_CSS_PATH = _find_first(["assets/*.css", "*.css"])


init_db()

# MCP server + UI resource

mcp = FastMCP(name="research-notes-py")
TEMPLATE_URI = "ui://widget/research-notes.html"


def _static_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Access-Control-Allow-Origin": "*",
    }


def _widget_csp() -> str:
    override = os.getenv("WIDGET_CSP", "").strip()
    if override:
        return override
    return (
        "default-src 'self'; "
        "script-src 'self' https: resource: 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' https: resource: 'unsafe-inline'; "
        "img-src 'self' https: data: blob:; "
        "font-src 'self' https: data:; "
        "connect-src 'self' https:; "
    )


def _widget_csp_meta() -> dict[str, object]:
    return {
        "openai/widgetCsp": _widget_csp(),
        "openai/widgetCSP": {"connect_domains": [], "resource_domains": []},
    }


def _wrap_widget_js(js: str) -> str:
    polyfill = (
        "(function(){"
        "if (typeof globalThis.TextEncoder === 'undefined') {"
        "function TE(){};"
        "TE.prototype.encode = function(str){"
        "str = String(str || '');"
        "var out = [], i = 0;"
        "for (; i < str.length; i++) {"
        "var c = str.charCodeAt(i);"
        "if (c < 0x80) { out.push(c); continue; }"
        "if (c < 0x800) { out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f)); continue; }"
        "if (c < 0xd800 || c >= 0xe000) {"
        "out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));"
        "continue; }"
        "i++;"
        "var c2 = str.charCodeAt(i);"
        "var u = 0x10000 + (((c & 0x3ff) << 10) | (c2 & 0x3ff));"
        "out.push(0xf0 | (u >> 18), 0x80 | ((u >> 12) & 0x3f), 0x80 | ((u >> 6) & 0x3f), 0x80 | (u & 0x3f));"
        "}"
        "return new Uint8Array(out);"
        "};"
        "globalThis.TextEncoder = TE;"
        "}"
        "if (typeof globalThis.TextDecoder === 'undefined') {"
        "function TD(){};"
        "TD.prototype.decode = function(bytes){"
        "if (!bytes) return '';"
        "var out = '', i = 0;"
        "var arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);"
        "while (i < arr.length) {"
        "var c = arr[i++];"
        "if (c < 0x80) { out += String.fromCharCode(c); continue; }"
        "if (c < 0xe0) {"
        "var c2 = arr[i++] & 0x3f;"
        "out += String.fromCharCode(((c & 0x1f) << 6) | c2);"
        "continue; }"
        "if (c < 0xf0) {"
        "var c2b = arr[i++] & 0x3f;"
        "var c3 = arr[i++] & 0x3f;"
        "out += String.fromCharCode(((c & 0x0f) << 12) | (c2b << 6) | c3);"
        "continue; }"
        "var c2c = arr[i++] & 0x3f;"
        "var c3b = arr[i++] & 0x3f;"
        "var c4 = arr[i++] & 0x3f;"
        "var u = ((c & 0x07) << 18) | (c2c << 12) | (c3b << 6) | c4;"
        "u -= 0x10000;"
        "out += String.fromCharCode(0xd800 + (u >> 10), 0xdc00 + (u & 0x3ff));"
        "}"
        "return out;"
        "};"
        "globalThis.TextDecoder = TD;"
        "}"
        "})();"
    )
    return (
        "if (!window.__IA_WIDGET_LOADED__) {"
        "window.__IA_WIDGET_LOADED__ = true;"
        "var root = document.getElementById('root');"
        "var showError = function(label, err) {"
        "  if (!root) { root = document.getElementById('root'); }"
        "  if (root) {"
        "    var msg = label + ': ' + (err && err.message ? err.message : String(err));"
        "    root.textContent = msg;"
        "  }"
        "};"
        "window.addEventListener('error', function(e) { showError('Widget error', e.error || e.message); });"
        "window.addEventListener('unhandledrejection', function(e) { showError('Widget error', e.reason || e); });"
        "try {"
        "  if (root) { root.textContent = 'Booting Instructor Assistant...'; }"
        f"{polyfill}"
        f"{js}"
        "} catch (err) {"
        "  showError('Widget boot error', err);"
        "}"
        "}"
    )


@mcp.custom_route("/widget.js", methods=["GET"], include_in_schema=False)
async def serve_widget_js(_: Request) -> Response:
    if WIDGET_JS_PATH and WIDGET_JS_PATH.exists():
        return Response(
            _wrap_widget_js(WIDGET_JS_PATH.read_text(encoding="utf-8")),
            media_type="application/javascript",
            headers=_static_headers(),
        )
    if WIDGET_JS:
        return Response(
            _wrap_widget_js(WIDGET_JS),
            media_type="application/javascript",
            headers=_static_headers(),
        )
    return PlainTextResponse("widget.js not found", status_code=404)


@mcp.custom_route("/widget.css", methods=["GET"], include_in_schema=False)
async def serve_widget_css(_: Request) -> Response:
    if WIDGET_CSS_PATH and WIDGET_CSS_PATH.exists():
        return Response(
            WIDGET_CSS_PATH.read_bytes(),
            media_type="text/css",
            headers=_static_headers(),
        )
    if WIDGET_CSS:
        return Response(
            WIDGET_CSS,
            media_type="text/css",
            headers=_static_headers(),
        )
    return PlainTextResponse("widget.css not found", status_code=404)


@mcp.resource("resource://widget.js", mime_type="application/javascript")
def widget_js_resource() -> str | bytes:
    if WIDGET_JS_PATH and WIDGET_JS_PATH.exists():
        return _wrap_widget_js(WIDGET_JS_PATH.read_text(encoding="utf-8"))
    return _wrap_widget_js(WIDGET_JS)


@mcp.resource("resource://widget.css", mime_type="text/css")
def widget_css_resource() -> str | bytes:
    if WIDGET_CSS_PATH and WIDGET_CSS_PATH.exists():
        return WIDGET_CSS_PATH.read_bytes()
    return WIDGET_CSS


@mcp.resource(
    TEMPLATE_URI,
    mime_type="text/html+skybridge",
    annotations={
        "openai/widgetAccessible": True,
        "openai/widgetPrefersBorder": True,
        **_widget_csp_meta(),
    },
)
def research_notes_widget() -> str:
    if not WIDGET_JS:
        return (
            "Widget bundle missing. Run: cd web && npm i && npm run build."
        )

    safe_js = _wrap_widget_js(WIDGET_JS).replace("</script", "<\\/script")
    inline_css = f"<style>{WIDGET_CSS}</style>\n" if WIDGET_CSS else ""

    return (
        '<div id="root">Loading Instructor Assistant...</div>\n'
        f"{inline_css}"
        f'<script type="module">\n{safe_js}\n</script>\n'
    )


async def _list_resources_with_meta() -> list[Resource]:
    items: list[Resource] = []
    for res in mcp._resource_manager.list_resources():  # type: ignore[attr-defined]
        meta = _widget_csp_meta() if str(res.uri) == TEMPLATE_URI else None
        items.append(
            Resource(
                uri=res.uri,
                name=res.name or "",
                title=res.title,
                description=res.description,
                mimeType=res.mime_type,
                icons=res.icons,
                annotations=res.annotations,
                _meta=meta,
            )
        )
    return items


# Re-register list_resources on the low-level server so _meta is preserved.
mcp._mcp_server.list_resources()(_list_resources_with_meta)  # type: ignore[attr-defined]


async def _read_resource_request(req: ReadResourceRequest) -> ServerResult:
    uri = req.params.uri
    context = mcp.get_context()
    resource = await mcp._resource_manager.get_resource(uri, context=context)  # type: ignore[attr-defined]
    content = await resource.read()
    meta = _widget_csp_meta() if str(uri) == TEMPLATE_URI else None

    if isinstance(content, bytes):
        blob = base64.b64encode(content).decode("ascii")
        contents = [
            BlobResourceContents(
                uri=uri,
                blob=blob,
                mimeType=resource.mime_type,
                _meta=meta,
            )
        ]
    else:
        contents = [
            TextResourceContents(
                uri=uri,
                text=content,
                mimeType=resource.mime_type,
                _meta=meta,
            )
        ]

    return ServerResult(ReadResourceResult(contents=contents, _meta=meta))


mcp._mcp_server.request_handlers[ReadResourceRequest] = _read_resource_request  # type: ignore[attr-defined]


META_UI = {
    "openai/outputTemplate": TEMPLATE_URI,
    "openai/widgetAccessible": True,
    **_widget_csp_meta(),
}
META_SILENT = {"openai/widgetAccessible": False}


def _ui_result(structured: Dict[str, Any], msg: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=msg)],
        structuredContent=structured,
        meta=META_UI,
    )


def _text_result(text: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        meta=META_SILENT,
    )


_VALID_NONCES: set[str] = set()


@mcp.tool(name="session_handshake", meta=META_SILENT)
def session_handshake() -> CallToolResult:
  """
  Returns a one-time UI nonce. The UI must include this 'nonce' in mutating tool calls.
  Suggestions that don't know the nonce cannot perform writes.
  """
  nonce = secrets.token_hex(16)
  _VALID_NONCES.add(nonce)
  return _text_result(json.dumps({"nonce": nonce}))


def _require_nonce(nonce: Optional[str]) -> Optional[str]:
    if not nonce or nonce not in _VALID_NONCES:
        return "Action blocked: missing/invalid UI session."
    return None


def _delete_paper_and_detach(paper_id: int) -> tuple[dict[str, Any], str]:
    msg = ""
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        conn.execute("UPDATE notes SET paper_id=NULL WHERE paper_id=?", (paper_id,))
        conn.execute("DELETE FROM sections WHERE paper_id=?", (paper_id,))
        cur = conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
        deleted = cur.rowcount or 0
        conn.execute("COMMIT")
        msg = "Deleted paper (notes retained)." if deleted else f"Paper {paper_id} not found."
    return render_library_structured(), msg


@mcp.tool(name="render_library", meta=META_UI)
def render_library() -> CallToolResult:
    data = render_library_structured()
    c = len(data.get("papers", []))
    return _ui_result(data, f"Showing {c} {'papers' if c != 1 else 'paper'} in your library.")


@mcp.tool(name="add_paper", meta=META_UI)
async def add_paper(url: str) -> CallToolResult:
    await add_paper_impl(url, url)
    return _ui_result(render_library_structured(), "Added paper and refreshed library.")


@mcp.tool(name="index_paper", meta=META_SILENT)
def index_paper(paperId: int | str) -> CallToolResult:
    payload = index_paper_impl(int(paperId))
    return _text_result(json.dumps(payload, ensure_ascii=False))


@mcp.tool(name="get_paper_chunk", meta=META_SILENT)
def get_paper_chunk(paperId: int | str, sectionId: int | str) -> CallToolResult:
    chunk = get_paper_chunk_impl(int(sectionId))
    return _text_result((chunk or {}).get("text", "") or "")


@mcp.tool(name="save_note", meta=META_UI)
def save_note(paperId: int | str, title: str, summary: str) -> CallToolResult:
    save_note_impl(int(paperId), summary, title)
    return _ui_result(render_library_structured(), "Saved note.")


@mcp.tool(name="delete_paper", meta=META_UI)
def delete_paper(paperId: int | str) -> CallToolResult:
    pid = int(paperId)
    structured, msg = _delete_paper_and_detach(pid)
    return _ui_result(structured, msg)


@mcp.tool(name="add_paper_tool", meta=META_UI)
async def add_paper_tool(input_str: str, source_url: str | None = None) -> CallToolResult:
    await add_paper_impl(input_str, source_url)
    return _ui_result(render_library_structured(), "Added paper and refreshed library.")


@mcp.tool(name="index_paper_tool", meta=META_SILENT)
def index_paper_tool(paper_id: int | str) -> CallToolResult:
    return index_paper(paper_id)


@mcp.tool(name="get_paper_chunk_tool", meta=META_SILENT)
def get_paper_chunk_tool(section_id: int | str) -> CallToolResult:
    return get_paper_chunk(0, section_id)


@mcp.tool(name="delete_paper_tool", meta=META_UI)
def delete_paper_tool(paper_id: int | str) -> CallToolResult:
    pid = int(paper_id)
    structured, msg = _delete_paper_and_detach(pid)
    return _ui_result(structured, msg)


@mcp.tool(name="list_notes_tool", meta=META_UI)
def list_notes_tool() -> CallToolResult:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT n.id, n.paper_id, n.title, n.body, n.created_at,
                   p.title AS paper_title
            FROM notes n
            LEFT JOIN papers p ON p.id = n.paper_id
            ORDER BY datetime(n.created_at) DESC, n.id DESC
        """
        ).fetchall()
    structured = render_library_structured()
    structured["notes"] = [dict(r) for r in rows]
    return _ui_result(structured, f"Loaded {len(structured['notes'])} notes.")


@mcp.tool(name="save_note_tool", meta=META_UI)
def save_note_tool(
    paper_id: Optional[int] = None,
    body: Optional[str] = None,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    note_id: Optional[int] = None,
    nonce: Optional[str] = None,
) -> CallToolResult:
    err = _require_nonce(nonce)
    if err:
        return _ui_result(render_library_structured(), err)

    text = body if body is not None else summary
    with get_conn() as conn:
        if note_id is not None:
            old = conn.execute(
                "SELECT paper_id, title, body FROM notes WHERE id=?", (note_id,)
            ).fetchone()
            if not old:
                return _ui_result(
                    render_library_structured(), f"Note {note_id} not found."
                )
            new_title = title if title is not None else (old["title"] or "Untitled")
            new_body = text if text is not None else (old["body"] or "")
            new_pid = paper_id if paper_id is not None else old["paper_id"]
            conn.execute(
                "UPDATE notes SET paper_id=?, title=?, body=? WHERE id=?",
                (new_pid, new_title, new_body, note_id),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT n.id, n.paper_id, n.title, n.body, n.created_at, p.title AS paper_title
                FROM notes n LEFT JOIN papers p ON p.id = n.paper_id
                WHERE n.id=?
            """,
                (note_id,),
            ).fetchone()
        else:
            if text is None:
                return _ui_result(
                    render_library_structured(),
                    "Provide note text via 'body' or 'summary'.",
                )
            conn.execute(
                "INSERT INTO notes (paper_id, title, body, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (paper_id, title or "Untitled", text),
            )
            nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            row = conn.execute(
                """
                SELECT n.id, n.paper_id, n.title, n.body, n.created_at, p.title AS paper_title
                FROM notes n LEFT JOIN papers p ON p.id = n.paper_id
                WHERE n.id=?
            """,
                (nid,),
            ).fetchone()

    structured = render_library_structured()
    if row:
        structured["note"] = dict(row)
    return _ui_result(structured, "Saved note.")


@mcp.tool(name="delete_note_tool", meta=META_UI)
def delete_note_tool(note_id: int, nonce: Optional[str] = None) -> CallToolResult:
    err = _require_nonce(nonce)
    if err:
        return _ui_result(render_library_structured(), err)
    with get_conn() as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
    return _ui_result(render_library_structured(), "Deleted note.")


@mcp.tool(name="save_question_set", meta=META_UI)
def save_question_set(
    prompt: str,
    items: list[dict],
    nonce: Optional[str] = None,
) -> CallToolResult:
    """
    Persist a generated question set.
    Also writes a Canvas-compatible .md file for this set (non-fatal if export fails).
    """
    err = _require_nonce(nonce)
    if err:
        return CallToolResult(
            content=[TextContent(type="text", text=err)],
            structuredContent={"error": err},
            meta=META_UI,
        )

    if not isinstance(items, list) or not items:
        return CallToolResult(
            content=[TextContent(type="text", text="No questions received.")],
            structuredContent={"error": "no_questions"},
            meta=META_UI,
        )

    try:
        payload = create_question_set(prompt, items)
    except ValueError as exc:
        return CallToolResult(
            content=[TextContent(type="text", text=str(exc))],
            structuredContent={"error": str(exc)},
            meta=META_UI,
        )

    questions = payload.get("questions") or []
    question_set = payload.get("question_set") or {}
    if question_set.get("canvas_md_path"):
        msg = f"Saved {len(questions)} questions and Canvas markdown."
    else:
        msg = f"Saved {len(questions)} questions."

    return CallToolResult(
        content=[TextContent(type="text", text=msg)],
        structuredContent=payload,
        meta=META_UI,
    )


@mcp.tool(name="save_question_set_tool", meta=META_UI)
def save_question_set_tool(
    prompt: str,
    items: list[dict],
    nonce: Optional[str] = None,
) -> CallToolResult:
    return save_question_set(prompt=prompt, items=items, nonce=nonce)


@mcp.tool(name="list_question_sets_tool", meta=META_UI)
def list_question_sets_tool(set_id: Optional[int] = None) -> CallToolResult:
    sc: Dict[str, Any] = {"question_sets": list_question_sets()}
    if set_id is not None:
        payload = get_question_set(int(set_id))
        if payload:
            sc.update(payload)

    return CallToolResult(
        content=[TextContent(type="text", text="Loaded question sets.")],
        structuredContent=sc,
        meta=META_UI,
    )


@mcp.tool(name="delete_question_set_tool", meta=META_UI)
def delete_question_set_tool(
    set_id: int,
    nonce: Optional[str] = None,
) -> CallToolResult:
    err = _require_nonce(nonce)
    if err:
        return CallToolResult(
            content=[TextContent(type="text", text=err)],
            structuredContent={"error": err},
            meta=META_UI,
        )

    delete_question_set(int(set_id))

    return CallToolResult(
        content=[TextContent(type="text", text="Deleted question set.")],
        structuredContent={},
        meta=META_UI,
    )


class SummarySchema(BaseModel):
    summary: str = Field(
        ...,
        description="250-400 word narrative summary",
    )
    bullets: str | None = Field(
        None,
        description="Five key takeaways, one per line starting with '- '",
    )
    limitations: str | None = Field(
        None,
        description="Three limitations, one per line starting with '- '",
    )


def _local_extractive_summary(excerpts: List[str]) -> Tuple[str, List[str], List[str]]:
    text = " ".join(excerpts)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    acc: List[str] = []
    wc = 0
    for s in sents:
        acc.append(s)
        wc += len(s.split())
        if wc >= 260:
            break
    if not acc:
        acc = sents[:5]
    summary = " ".join(" ".join(acc).split()[:400])

    rest = sents[len(acc):]
    bullets: List[str] = []
    for s in rest:
        if len(bullets) >= 5:
            break
        bullets.append(s)

    limits = [
        "Refer to the full paper for methodology details.",
        "Automated extractive summary may omit key nuances.",
        "Validate conclusions against original figures and tables.",
    ]
    return summary, bullets, limits


def _compose_note(summary: str, bullets: List[str], limits: List[str]) -> str:
    parts: List[str] = [summary.strip()]
    if bullets:
        parts.append(
            "Key takeaways:\n"
            + "\n".join(f"- {b.strip()}" for b in bullets[:5])
        )
    if limits:
        parts.append(
            "Limitations:\n"
            + "\n".join(f"- {l.strip()}" for l in limits[:3])
        )
    return "\n\n".join(parts).strip()


@mcp.tool(name="summarize_paper_tool", meta=META_UI)
def summarize_paper_tool(
    paper_id: int,
    context: Context | None = None,
) -> CallToolResult:
    """
    Fallback summarization: index locally, build an extractive summary, and save as a note.
    (Your UI can still trigger a richer map/reduce flow via sendFollowUpMessage.)
    """
    try:
        index_paper_impl(int(paper_id))
    except Exception:
        # Indexing is best-effort here; continue with whatever sections exist.
        pass

    excerpts: List[str] = []
    total = 0
    cap = 9000

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT page_no, text FROM sections WHERE paper_id=? ORDER BY page_no ASC",
            (paper_id,),
        ).fetchall()
        paper = conn.execute(
            "SELECT title FROM papers WHERE id=?",
            (paper_id,),
        ).fetchone()
        paper_title = (paper["title"] if paper else "Paper Summary") or "Paper Summary"

    for r in rows:
        t = (r["text"] or "").strip()
        if not t:
            continue
        snip = f"[Page {r['page_no']}] {t}"
        if total + len(snip) > cap:
            snip = snip[: (cap - total)]
        excerpts.append(snip)
        total += len(snip)
        if total >= cap:
            break

    summary, bullets, limits = _local_extractive_summary(excerpts)
    body = (
        "*Automated extractive summary (model follow-up path unavailable).*"
        "\n\n"
        + _compose_note(summary, bullets, limits)
    )

    save_note_impl(int(paper_id), body, f"Summary — {paper_title}")
    return _ui_result(
        render_library_structured(),
        "Summary saved to notes (fallback).",
    )


# Run server

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
