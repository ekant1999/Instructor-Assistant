from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_LOG_DIR = BACKEND_ROOT / "logs" / "mcp_mock"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _truncate(value: Any, *, max_chars: int = 400, max_items: int = 5) -> Any:
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + "...[truncated]"
    if isinstance(value, list):
        preview = [_truncate(item, max_chars=max_chars, max_items=max_items) for item in value[:max_items]]
        if len(value) > max_items:
            preview.append(f"...[{len(value) - max_items} more item(s)]")
        return preview
    if isinstance(value, dict):
        return {
            str(key): _truncate(val, max_chars=max_chars, max_items=max_items)
            for key, val in list(value.items())[:30]
        }
    return value


class EventLogger:
    def __init__(self, log_dir: Path, scenario_name: str) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.text_path = log_dir / f"{stamp}_{scenario_name}.log"
        self.jsonl_path = log_dir / f"{stamp}_{scenario_name}.jsonl"

        self.logger = logging.getLogger(f"mock-library-mcp.{stamp}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False

        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler = logging.FileHandler(self.text_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def event(self, kind: str, **payload: Any) -> None:
        safe = {key: _truncate(val) for key, val in payload.items()}
        self.logger.info("[%s] %s", kind, json.dumps(safe, ensure_ascii=False))
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": datetime.now().isoformat(), "kind": kind, **safe}, ensure_ascii=False) + "\n")


def _normalize_direct_result(result: Any) -> Dict[str, Any]:
    content_blocks = getattr(result, "content", None) or []
    text_parts = []
    for block in content_blocks:
        text = getattr(block, "text", None)
        if text:
            text_parts.append(text)
    return {
        "message": "\n".join(text_parts).strip(),
        "structured": getattr(result, "structuredContent", None) or {},
        "is_error": bool(getattr(result, "isError", False)),
    }


def _build_tool_caller(mode: str) -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
    if mode == "mcp":
        from backend.mcp_client import call_tool

        def _call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            structured = call_tool(name, arguments)
            return {"message": "", "structured": structured, "is_error": False}

        return _call

    from backend.mcp_server import app as mcp_app

    direct_tools = {
        "find_library_paper": mcp_app.find_library_paper_tool,
        "get_library_pdf": mcp_app.get_library_pdf_tool,
        "get_library_excerpt": mcp_app.get_library_excerpt_tool,
        "list_library_sections": mcp_app.list_library_sections_tool,
        "get_library_section": mcp_app.get_library_section_tool,
        "list_library_figures": mcp_app.list_library_figures_tool,
        "get_library_figure": mcp_app.get_library_figure_tool,
        "load_library_paper_context": mcp_app.load_library_paper_context_tool,
        "list_contexts": mcp_app.list_contexts,
        "read_context": mcp_app.read_context,
    }

    def _call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fn = direct_tools.get(name)
        if fn is None:
            raise ValueError(f"Unsupported tool in direct mode: {name}")
        return _normalize_direct_result(fn(**arguments))

    return _call


def _call_tool(
    logger: EventLogger,
    caller: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    *,
    llm_request: str,
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    logger.event("llm_request", request=llm_request)
    logger.event("tool_call", tool=tool_name, arguments=arguments)
    result = caller(tool_name, arguments)
    logger.event("tool_response", tool=tool_name, response=result)
    if result.get("is_error"):
        raise RuntimeError(result.get("message") or f"Tool {tool_name} returned an error.")
    return result


def _validate_base64_payload(
    payload: Dict[str, Any],
    *,
    expected_delivery: str,
    expected_mime_prefix: str,
    label: str,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} did not return a structured payload.")
    delivery = str(payload.get("delivery") or "").strip().lower()
    if delivery != expected_delivery:
        raise RuntimeError(f"{label} returned delivery={delivery!r}, expected {expected_delivery!r}.")
    mime_type = str(payload.get("mime_type") or "").strip().lower()
    if not mime_type.startswith(expected_mime_prefix):
        raise RuntimeError(f"{label} returned mime_type={mime_type!r}, expected prefix {expected_mime_prefix!r}.")
    data_b64 = str(payload.get("data_b64") or "")
    size_bytes = int(payload.get("size_bytes") or 0)
    if not data_b64:
        raise RuntimeError(f"{label} returned empty base64 data.")
    if size_bytes <= 0:
        raise RuntimeError(f"{label} returned non-positive size_bytes.")
    return {
        "delivery": delivery,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "data_b64_length": len(data_b64),
        "filename": payload.get("filename") or payload.get("figure_name"),
    }


def run_scenario(args: argparse.Namespace) -> Dict[str, Any]:
    logger = EventLogger(Path(args.log_dir), "library_mcp_flows")
    caller = _build_tool_caller(args.mode)
    summary: Dict[str, Any] = {"mode": args.mode}

    find_result = _call_tool(
        logger,
        caller,
        llm_request=f"Find the research paper matching '{args.paper_query}'.",
        tool_name="find_library_paper",
        arguments={"query": args.paper_query, "limit": 5, "search_type": args.search_type},
    )
    papers = ((find_result.get("structured") or {}).get("papers") or [])
    if not papers:
        raise RuntimeError("No papers were returned by find_library_paper.")
    paper = papers[0]
    paper_id = int(paper["paper_id"])
    summary["paper_id"] = paper_id
    summary["paper_title"] = paper.get("title")

    pdf_result = _call_tool(
        logger,
        caller,
        llm_request=f"Get the PDF reference for paper {paper_id}.",
        tool_name="get_library_pdf",
        arguments={"paper_id": paper_id, "delivery": "reference"},
    )
    summary["pdf_reference"] = ((pdf_result.get("structured") or {}).get("paper") or {}).get("reference")

    if args.test_pdf_base64:
        pdf_base64_result = _call_tool(
            logger,
            caller,
            llm_request=f"Return the actual PDF bytes for paper {paper_id} as base64.",
            tool_name="get_library_pdf",
            arguments={
                "paper_id": paper_id,
                "delivery": "base64",
                "max_inline_bytes": args.pdf_base64_max_bytes,
            },
        )
        pdf_payload = ((pdf_base64_result.get("structured") or {}).get("paper") or {})
        summary["pdf_base64"] = _validate_base64_payload(
            pdf_payload,
            expected_delivery="base64",
            expected_mime_prefix="application/pdf",
            label="get_library_pdf(base64)",
        )

    excerpt_query = args.excerpt_query or args.paper_query
    excerpt_result = _call_tool(
        logger,
        caller,
        llm_request=f"Give me the most relevant excerpt for '{excerpt_query}' from paper {paper_id}.",
        tool_name="get_library_excerpt",
        arguments={
            "paper_id": paper_id,
            "query": excerpt_query,
            "max_chars": args.max_chars,
            "search_type": args.search_type,
            "limit": 5,
        },
    )
    summary["excerpt"] = (excerpt_result.get("structured") or {}).get("excerpt")

    sections_result = _call_tool(
        logger,
        caller,
        llm_request=f"List the available canonical sections for paper {paper_id}.",
        tool_name="list_library_sections",
        arguments={"paper_id": paper_id},
    )
    sections = ((sections_result.get("structured") or {}).get("sections") or [])
    target_section = args.section_canonical
    if not target_section:
        for candidate in sections:
            canonical = str(candidate.get("canonical") or "").strip().lower()
            if canonical and canonical not in {"front_matter", "references", "other"}:
                target_section = canonical
                break
    if target_section:
        section_result = _call_tool(
            logger,
            caller,
            llm_request=f"Give me the '{target_section}' section from paper {paper_id}.",
            tool_name="get_library_section",
            arguments={"paper_id": paper_id, "section_canonical": target_section, "max_chars": args.max_chars * 4},
        )
        summary["section"] = (section_result.get("structured") or {}).get("section_canonical") or target_section

    figures_result = _call_tool(
        logger,
        caller,
        llm_request=f"List figures available in paper {paper_id}.",
        tool_name="list_library_figures",
        arguments={"paper_id": paper_id, "limit": 10},
    )
    figures = ((figures_result.get("structured") or {}).get("figures") or [])
    target_figure = args.figure_name or (figures[0]["figure_name"] if figures else None)
    if target_figure:
        figure_result = _call_tool(
            logger,
            caller,
            llm_request=f"Give me the figure named '{target_figure}' from paper {paper_id}.",
            tool_name="get_library_figure",
            arguments={"paper_id": paper_id, "figure_name": target_figure, "delivery": "reference"},
        )
        summary["figure"] = ((figure_result.get("structured") or {}).get("reference") or {})

        if args.test_figure_base64:
            figure_base64_result = _call_tool(
                logger,
                caller,
                llm_request=f"Return the actual image bytes for figure '{target_figure}' from paper {paper_id} as base64.",
                tool_name="get_library_figure",
                arguments={
                    "paper_id": paper_id,
                    "figure_name": target_figure,
                    "delivery": "base64",
                    "max_inline_bytes": args.figure_base64_max_bytes,
                },
            )
            figure_payload = figure_base64_result.get("structured") or {}
            summary["figure_base64"] = _validate_base64_payload(
                figure_payload,
                expected_delivery="base64",
                expected_mime_prefix="image/",
                label="get_library_figure(base64)",
            )

    context_result = _call_tool(
        logger,
        caller,
        llm_request=f"Load paper {paper_id} into the MCP context store so I can read it incrementally.",
        tool_name="load_library_paper_context",
        arguments={"paper_id": paper_id, "max_chars": args.max_chars * 8},
    )
    context = ((context_result.get("structured") or {}).get("context") or {})
    context_id = str(context.get("context_id") or "")
    if not context_id:
        raise RuntimeError("Context tool did not return a context_id.")
    summary["context_id"] = context_id

    _call_tool(
        logger,
        caller,
        llm_request="Show me all currently available contexts.",
        tool_name="list_contexts",
        arguments={},
    )
    read_result = _call_tool(
        logger,
        caller,
        llm_request=f"Read the first {args.read_length} characters from context {context_id}.",
        tool_name="read_context",
        arguments={"context_id": context_id, "start": 0, "length": args.read_length},
    )
    summary["read_context"] = (read_result.get("structured") or {}).get("content")

    logger.event("scenario_complete", summary=summary, text_log=str(logger.text_path), jsonl_log=str(logger.jsonl_path))
    return {"summary": summary, "text_log": str(logger.text_path), "jsonl_log": str(logger.jsonl_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mock LLM -> MCP library tool flow runner with verbose logging.")
    parser.add_argument("--mode", choices=["direct", "mcp"], default="direct", help="Use direct function calls or real MCP client transport.")
    parser.add_argument("--paper-query", default="WorldCam", help="Paper query used for the first lookup step.")
    parser.add_argument("--excerpt-query", default=None, help="Query used for the excerpt step. Defaults to --paper-query.")
    parser.add_argument("--section-canonical", default=None, help="Optional canonical section to fetch.")
    parser.add_argument("--figure-name", default=None, help="Optional explicit figure name to fetch.")
    parser.add_argument("--search-type", choices=["keyword", "embedding", "hybrid"], default="hybrid")
    parser.add_argument("--test-pdf-base64", action="store_true", help="Also validate get_library_pdf with delivery=base64.")
    parser.add_argument("--pdf-base64-max-bytes", type=int, default=10_000_000, help="Inline byte ceiling used for PDF base64 validation.")
    parser.add_argument("--test-figure-base64", action="store_true", help="Also validate get_library_figure with delivery=base64.")
    parser.add_argument("--figure-base64-max-bytes", type=int, default=5_242_880, help="Inline byte ceiling used for figure base64 validation.")
    parser.add_argument("--max-chars", type=int, default=4000, help="Character limit used for text-returning tool steps.")
    parser.add_argument("--read-length", type=int, default=3000, help="Character window used for read_context.")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR), help="Directory for human-readable and JSONL logs.")
    return parser.parse_args()


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    args = parse_args()
    result = run_scenario(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
