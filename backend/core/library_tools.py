from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

from .async_utils import run_async_blocking
from .database import get_conn
from .hybrid_search import full_text_search, hybrid_search
from .postgres import close_pool as close_pg_pool
from .postgres import get_pool as get_pg_pool
from .search import search_sections
from .search_context import (
    build_match_snippet,
    pgvector_score,
    query_tokens,
    select_block_for_query,
)
from .search_pipeline import (
    aggregate_section_hits_to_papers,
    filter_aggregated_papers_for_query,
    filter_section_hits_for_query,
    infer_search_section_bucket,
    inject_title_only_candidates,
    paper_title_bonus_lookup,
    rrf_score,
    search_paper_sections_for_localization,
    search_section_hits_unified,
    section_bucket_multiplier,
    token_overlap,
)
from .storage import (
    get_paper_asset,
    get_primary_pdf_asset,
    open_paper_asset_stream,
    open_primary_pdf_stream,
    paper_ids_with_primary_pdf_assets,
    resolve_local_pdf_path,
)
from ..rag import equation_extractor, paper_figures, table_extractor
from ..rag.pgvector_store import PgVectorStore
from ..schemas import QuestionContextUploadResponse


logger = logging.getLogger(__name__)

DEFAULT_TOOL_SEARCH_TYPE = "hybrid"
DEFAULT_INLINE_MAX_BYTES = 5 * 1024 * 1024


def _api_reference(path: str) -> Dict[str, Any]:
    api_path = str(path or "").strip()
    payload: Dict[str, Any] = {"api_path": api_path}
    base = os.getenv("LIBRARY_TOOL_API_BASE", "").strip().rstrip("/")
    if base and api_path:
        payload["api_url"] = f"{base}{api_path}"
    return payload


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


def _coalesce_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _get_paper_row(paper_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, title, source_url, pdf_path, rag_status, rag_error,
                   rag_updated_at, created_at
            FROM papers
            WHERE id = ?
            """,
            (paper_id,),
        ).fetchone()
    return dict(row) if row else None


def _paper_payload(row: Dict[str, Any], *, score: Optional[float] = None, best_hit: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    paper_id = int(row["id"])
    has_asset = paper_id in paper_ids_with_primary_pdf_assets([paper_id])
    pdf_available = bool(row.get("pdf_path")) or has_asset
    payload: Dict[str, Any] = {
        "paper_id": paper_id,
        "title": row.get("title"),
        "source_url": row.get("source_url"),
        "rag_status": row.get("rag_status"),
        "pdf_available": pdf_available,
        "pdf_reference": _api_reference(f"/api/papers/{paper_id}/file") if pdf_available else None,
    }
    if score is not None:
        payload["score"] = float(score)
    if best_hit:
        payload["best_match"] = {
            "page_no": best_hit.get("page_no"),
            "section_id": best_hit.get("id"),
            "section_canonical": best_hit.get("match_section_canonical"),
            "snippet": best_hit.get("match_text"),
            "bbox": best_hit.get("match_bbox"),
        }
    return payload


def _read_stream_bytes(response: Any, *, max_bytes: int) -> bytes:
    chunks = bytearray()
    try:
        for chunk in response.stream(1024 * 1024):
            chunks.extend(chunk)
            if len(chunks) > max_bytes:
                raise ValueError(f"Object exceeds inline byte limit ({max_bytes} bytes).")
        return bytes(chunks)
    finally:
        response.close()
        response.release_conn()


def _read_primary_pdf_bytes(paper_id: int, *, max_bytes: int) -> Tuple[bytes, str, str]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    local_path = resolve_local_pdf_path(paper.get("pdf_path"))
    if local_path and local_path.exists():
        data = local_path.read_bytes()
        if len(data) > max_bytes:
            raise ValueError(f"PDF exceeds inline byte limit ({max_bytes} bytes).")
        return data, local_path.name, "application/pdf"

    asset, response = open_primary_pdf_stream(paper_id)
    if asset is None or response is None:
        raise ValueError("PDF not available for this paper.")

    filename = str(asset.get("original_filename") or f"paper-{paper_id}.pdf")
    mime_type = str(asset.get("mime_type") or "application/pdf")
    return _read_stream_bytes(response, max_bytes=max_bytes), filename, mime_type


def _read_figure_bytes(paper_id: int, figure_name: str, *, max_bytes: int) -> Tuple[bytes, str, str]:
    figure_path = paper_figures.resolve_figure_file(paper_id, figure_name)
    if figure_path.exists():
        data = figure_path.read_bytes()
        if len(data) > max_bytes:
            raise ValueError(f"Image exceeds inline byte limit ({max_bytes} bytes).")
        return data, Path(figure_name).name, "image/png"

    safe_name = Path(figure_name).name
    asset = get_paper_asset(paper_id, role="figure_image", original_filename=safe_name)
    asset, response = open_paper_asset_stream(asset)
    if asset is None or response is None:
        raise ValueError("Figure image not found.")
    mime_type = str(asset.get("mime_type") or "application/octet-stream")
    return _read_stream_bytes(response, max_bytes=max_bytes), safe_name, mime_type


def _asset_api_reference(
    item: Dict[str, Any],
    *,
    paper_id: int,
    route_prefix: str,
    file_name: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not file_name:
        return None
    existing_url = str(item.get("url") or "").strip()
    if existing_url.startswith("/api/"):
        return _api_reference(existing_url)
    resolved_paper_id = int(item.get("paper_id") or paper_id)
    return _api_reference(f"/api/papers/{resolved_paper_id}/{route_prefix}/{quote(file_name)}")


def _simplify_figure(item: Dict[str, Any], *, paper_id: int) -> Dict[str, Any]:
    name = str(item.get("file_name") or "").strip()
    return {
        "figure_name": name,
        "page_no": int(item.get("page_no") or 0),
        "section_canonical": str(item.get("section_canonical") or "").strip() or None,
        "section_title": str(item.get("section_title") or "").strip() or None,
        "figure_type": str(item.get("figure_type") or "").strip() or None,
        "caption": str(item.get("figure_caption") or "").strip() or None,
        "bbox": item.get("bbox") if isinstance(item.get("bbox"), dict) else None,
        "image_reference": _asset_api_reference(item, paper_id=paper_id, route_prefix="figures", file_name=name),
    }


def _simplify_equation(item: Dict[str, Any], *, paper_id: int) -> Dict[str, Any]:
    file_name = str(item.get("file_name") or "").strip() or None
    return {
        "id": int(item.get("id") or 0),
        "page_no": int(item.get("page_no") or 0),
        "equation_number": str(item.get("equation_number") or "").strip() or None,
        "text": str(item.get("text") or "").strip() or "",
        "section_canonical": str(item.get("section_canonical") or "").strip() or None,
        "section_title": str(item.get("section_title") or "").strip() or None,
        "bbox": item.get("bbox") if isinstance(item.get("bbox"), dict) else None,
        "image_reference": _asset_api_reference(item, paper_id=paper_id, route_prefix="equations", file_name=file_name),
        "json_file": str(item.get("json_file") or "").strip() or None,
    }


def _simplify_table(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(item.get("id") or 0),
        "page_no": int(item.get("page_no") or 0),
        "caption": str(item.get("caption") or "").strip() or None,
        "section_canonical": str(item.get("section_canonical") or "").strip() or None,
        "section_title": str(item.get("section_title") or "").strip() or None,
        "bbox": item.get("bbox") if isinstance(item.get("bbox"), dict) else None,
        "n_rows": int(item.get("n_rows") or 0),
        "n_cols": int(item.get("n_cols") or 0),
        "json_file": str(item.get("json_file") or "").strip() or None,
    }


def _select_section_manifest_items(
    items: List[Dict[str, Any]],
    *,
    target: str,
    pages: List[int],
) -> List[Dict[str, Any]]:
    exact = [
        item for item in items
        if str(item.get("section_canonical") or "").strip().lower() == target
    ]
    if exact:
        return exact
    if not pages:
        return []
    page_set = set(pages)
    fallback: List[Dict[str, Any]] = []
    for item in items:
        if int(item.get("page_no") or 0) not in page_set:
            continue
        section_canonical = str(item.get("section_canonical") or "").strip().lower()
        if section_canonical and section_canonical not in {"other", "unknown", "unassigned"}:
            continue
        fallback.append(item)
    return fallback


def _keyword_match_lookup_for_sections(paper_id: int, query: str, limit: int = 200) -> Dict[int, Dict[str, Any]]:
    enriched_rows = _pgvector_search_section_hits(
        query,
        "keyword",
        [paper_id],
        include_text=False,
        max_chars=None,
        limit=limit,
    )
    lookup: Dict[int, Dict[str, Any]] = {}
    for row in enriched_rows:
        try:
            section_id = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        payload: Dict[str, Any] = {}
        if row.get("match_bbox") is not None:
            payload["match_bbox"] = row.get("match_bbox")
        if row.get("match_block_index") is not None:
            payload["match_block_index"] = row.get("match_block_index")
        if row.get("match_section_canonical"):
            payload["match_section_canonical"] = row.get("match_section_canonical")
        if row.get("match_text"):
            payload["match_text"] = row.get("match_text")
        if payload:
            lookup[section_id] = payload
    return lookup


def _keyword_section_hits(
    query: str,
    paper_ids: Optional[List[int]] = None,
    *,
    include_text: bool,
    max_chars: Optional[int],
    limit: int,
) -> List[Dict[str, Any]]:
    rows = search_sections(query, search_type="keyword", paper_ids=paper_ids, limit=limit)
    if not rows:
        return []

    tokens = query_tokens(query)
    match_lookup: Dict[int, Dict[str, Any]] = {}
    if paper_ids and len(paper_ids) == 1:
        match_lookup = _keyword_match_lookup_for_sections(paper_ids[0], query, limit=max(limit, 200))

    hits: List[Dict[str, Any]] = []
    query_l = (query or "").strip().lower()
    for idx, row in enumerate(rows):
        section_id = int(row["id"])
        text = str(row.get("text") or "")
        matched = match_lookup.get(section_id) or {}
        lex_hits = token_overlap(tokens, text)
        exact_phrase = bool(query_l and len(query_l) >= 3 and query_l in text.lower())
        keyword_score = rrf_score(idx, k=10)
        if exact_phrase:
            keyword_score += 0.08
        keyword_score += min(lex_hits, 4) * 0.015
        search_bucket = infer_search_section_bucket(
            text,
            page_no=int(row["page_no"]),
            section_canonical=matched.get("match_section_canonical"),
        )

        entry: Dict[str, Any] = {
            "id": section_id,
            "paper_id": int(row["paper_id"]),
            "page_no": int(row["page_no"]),
            "match_score": keyword_score * section_bucket_multiplier(search_bucket),
            "keyword_score": keyword_score,
            "semantic_score": 0.0,
            "semantic_raw_score": 0.0,
            "block_match_score": float(lex_hits) + (8.0 if exact_phrase else 0.0),
            "lex_hits": lex_hits,
            "exact_phrase": exact_phrase,
            "match_bbox": matched.get("match_bbox"),
            "match_block_index": matched.get("match_block_index"),
            "match_section_canonical": matched.get("match_section_canonical"),
            "search_bucket": search_bucket,
            "source_text": text,
        }
        snippet = matched.get("match_text") or build_match_snippet(query, tokens, text)
        if snippet:
            entry["match_text"] = snippet
        if include_text:
            trimmed = text[:max_chars] if max_chars is not None and max_chars > 0 else text
            entry["text"] = trimmed
        hits.append(entry)
    hits.sort(key=lambda item: item.get("match_score", 0.0), reverse=True)
    return hits


def _pgvector_search_section_hits(
    query: str,
    search_type: str,
    paper_ids: Optional[List[int]] = None,
    *,
    include_text: bool,
    max_chars: Optional[int],
    limit: int = 100,
) -> List[Dict[str, Any]]:
    async def _run() -> List[Dict[str, Any]]:
        try:
            alpha_raw = os.getenv("HYBRID_SEARCH_ALPHA", "0.5")
            try:
                alpha = float(alpha_raw)
            except ValueError:
                alpha = 0.5
            pool = await get_pg_pool()
            store = PgVectorStore(pool)
            retrieve_k = max(20, min(limit * 5, 300))
            if search_type == "embedding":
                return await store.similarity_search(query, k=retrieve_k, paper_ids=paper_ids)
            if search_type == "keyword":
                return await full_text_search(query, pool, k=retrieve_k, paper_ids=paper_ids)
            return await hybrid_search(query, store, pool, k=retrieve_k, paper_ids=paper_ids, alpha=alpha)
        finally:
            try:
                await close_pg_pool()
            except Exception:
                pass

    try:
        results = run_async_blocking(_run)
    except Exception:
        logger.exception("pgvector section search failed in library tool helper")
        return []

    if not results:
        return []

    tokens = query_tokens(query)
    page_scores: Dict[Tuple[int, int], float] = {}
    page_best: Dict[Tuple[int, int], Dict[str, Any]] = {}
    page_best_match: Dict[Tuple[int, int], Dict[str, Any]] = {}
    for idx, row in enumerate(results):
        pid = row.get("paper_id")
        if pid is None:
            continue
        match_block = select_block_for_query(row, tokens, query)
        page_no = match_block.get("page_no") or row.get("page_no")
        if not page_no:
            continue
        raw_score = pgvector_score(row)
        semantic_score = rrf_score(idx, k=15) + min(max(raw_score, 0.0), 1.0) * 0.15
        key = (int(pid), int(page_no))
        row_block_index = _coalesce_not_none(match_block.get("block_index"), row.get("block_index"))
        row_bbox = _coalesce_not_none(match_block.get("bbox"), row.get("bbox"))
        row_text = match_block.get("text") or row.get("text")
        row_lex_hits = int(match_block.get("lex_hits") or 0)
        row_match_score = float(match_block.get("match_score") or 0.0)
        row_exact_phrase = bool(match_block.get("exact_phrase") or False)
        row_section_canonical = str(match_block.get("section_canonical") or "")

        prev = page_scores.get(key)
        if prev is None or semantic_score > prev:
            page_scores[key] = semantic_score
            page_best[key] = {
                "bbox": row_bbox,
                "block_index": row_block_index,
                "text": row_text,
                "lex_hits": row_lex_hits,
                "match_score": row_match_score,
                "exact_phrase": row_exact_phrase,
                "section_canonical": row_section_canonical,
                "semantic_score": semantic_score,
                "semantic_raw_score": raw_score,
            }

        prev_match = page_best_match.get(key)
        if prev_match is None:
            page_best_match[key] = {
                "bbox": row_bbox,
                "block_index": row_block_index,
                "text": row_text,
                "lex_hits": row_lex_hits,
                "match_score": row_match_score,
                "exact_phrase": row_exact_phrase,
                "section_canonical": row_section_canonical,
                "semantic_score": semantic_score,
                "semantic_raw_score": raw_score,
            }
        else:
            prev_key = (
                bool(prev_match.get("exact_phrase")),
                float(prev_match.get("match_score") or 0.0),
                int(prev_match.get("lex_hits") or 0),
                float(prev_match.get("semantic_score") or 0.0),
            )
            curr_key = (
                row_exact_phrase,
                row_match_score,
                row_lex_hits,
                semantic_score,
            )
            if curr_key > prev_key:
                page_best_match[key] = {
                    "bbox": row_bbox,
                    "block_index": row_block_index,
                    "text": row_text,
                    "lex_hits": row_lex_hits,
                    "match_score": row_match_score,
                    "exact_phrase": row_exact_phrase,
                    "section_canonical": row_section_canonical,
                    "semantic_score": semantic_score,
                    "semantic_raw_score": raw_score,
                }

    if not page_scores:
        return []

    paper_list = sorted({paper_id for paper_id, _ in page_scores.keys()})
    page_list = sorted({page_no for _, page_no in page_scores.keys()})
    paper_placeholders = ",".join("?" for _ in paper_list)
    page_placeholders = ",".join("?" for _ in page_list)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, paper_id, page_no, text
            FROM sections
            WHERE paper_id IN ({paper_placeholders}) AND page_no IN ({page_placeholders})
            """,
            (*paper_list, *page_list),
        ).fetchall()

    sections: List[Dict[str, Any]] = []
    for row in rows:
        key = (int(row["paper_id"]), int(row["page_no"]))
        if key not in page_scores:
            continue
        best = page_best.get(key) or {}
        matched = page_best_match.get(key)
        if matched and tokens:
            min_hits = 1 if len(tokens) <= 3 else 2
            if bool(matched.get("exact_phrase")) or int(matched.get("lex_hits", 0)) >= min_hits:
                best = matched
        search_bucket = infer_search_section_bucket(
            str((row["text"] or "") or best.get("text") or ""),
            page_no=int(row["page_no"]),
            section_canonical=best.get("section_canonical"),
        )
        entry: Dict[str, Any] = {
            "id": int(row["id"]),
            "page_no": int(row["page_no"]),
            "paper_id": int(row["paper_id"]),
            "match_score": page_scores.get(key, 0.0) * section_bucket_multiplier(search_bucket),
            "keyword_score": 0.0,
            "semantic_score": float(best.get("semantic_score") or page_scores.get(key, 0.0)),
            "semantic_raw_score": float(best.get("semantic_raw_score") or 0.0),
            "block_match_score": float(best.get("match_score") or 0.0),
            "lex_hits": int(best.get("lex_hits") or 0),
            "exact_phrase": bool(best.get("exact_phrase") or False),
            "match_bbox": best.get("bbox"),
            "match_block_index": best.get("block_index"),
            "match_section_canonical": best.get("section_canonical"),
            "search_bucket": search_bucket,
            "source_text": best.get("text") or row["text"] or "",
        }
        best_text = str(best.get("text") or "")
        match_text = build_match_snippet(query, tokens, best_text)
        if match_text:
            entry["match_text"] = match_text
        if include_text:
            text = str(row["text"] or "")
            if max_chars is not None and max_chars > 0:
                text = text[:max_chars]
            entry["text"] = text
        sections.append(entry)

    sections.sort(key=lambda item: item.get("match_score", 0.0), reverse=True)
    return sections[:limit]


def find_library_papers(
    query: str,
    *,
    limit: int = 5,
    search_type: str = DEFAULT_TOOL_SEARCH_TYPE,
) -> List[Dict[str, Any]]:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required.")

    if q.isdigit():
        row = _get_paper_row(int(q))
        return [_paper_payload(row, score=1.0)] if row else []

    st = str(search_type or DEFAULT_TOOL_SEARCH_TYPE).strip().lower()
    if st not in {"keyword", "embedding", "hybrid"}:
        st = DEFAULT_TOOL_SEARCH_TYPE

    section_hits = search_section_hits_unified(
        q,
        st,
        keyword_section_hits_fn=_keyword_section_hits,
        semantic_section_hits_fn=_pgvector_search_section_hits,
        paper_ids=None,
        include_text=False,
        max_chars=None,
        limit=max(50, limit * 10),
    )
    section_hits = filter_section_hits_for_query(q, section_hits, get_conn_fn=get_conn)
    title_bonus_by_id = paper_title_bonus_lookup(q, limit=max(100, limit * 5)) if st in {"keyword", "hybrid"} else {}
    aggregated = aggregate_section_hits_to_papers(section_hits, title_bonus_by_id, get_conn_fn=get_conn)
    aggregated = inject_title_only_candidates(aggregated, title_bonus_by_id, get_conn_fn=get_conn)
    aggregated = filter_aggregated_papers_for_query(q, aggregated, get_conn_fn=get_conn)

    if aggregated:
        paper_ids = list(aggregated.keys())
        placeholders = ",".join("?" for _ in paper_ids)
        with get_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT id, title, source_url, pdf_path, rag_status, rag_error,
                       rag_updated_at, created_at
                FROM papers
                WHERE id IN ({placeholders})
                """,
                tuple(paper_ids),
            ).fetchall()
        by_id = {int(row["id"]): dict(row) for row in rows}
        ordered_ids = sorted(
            aggregated.keys(),
            key=lambda pid: float((aggregated.get(pid) or {}).get("score", float("-inf"))),
            reverse=True,
        )
        results: List[Dict[str, Any]] = []
        for paper_id in ordered_ids[:limit]:
            row = by_id.get(int(paper_id))
            if not row:
                continue
            meta = aggregated.get(int(paper_id)) or {}
            results.append(_paper_payload(row, score=meta.get("score"), best_hit=meta.get("best_hit")))
        if results:
            return results

    q_like = f"%{q.lower()}%"
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, source_url, pdf_path, rag_status, rag_error,
                   rag_updated_at, created_at
            FROM papers
            WHERE lower(coalesce(title, '')) LIKE ? OR lower(coalesce(source_url, '')) LIKE ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (q_like, q_like, limit),
        ).fetchall()
    return [_paper_payload(dict(row)) for row in rows]


def get_library_pdf(
    paper_id: int,
    *,
    delivery: str = "reference",
    max_inline_bytes: int = DEFAULT_INLINE_MAX_BYTES,
) -> Dict[str, Any]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    reference = _api_reference(f"/api/papers/{paper_id}/file")
    if delivery == "reference":
        asset = get_primary_pdf_asset(paper_id)
        filename = None
        mime_type = "application/pdf"
        size_bytes = None
        if asset:
            filename = asset.get("original_filename")
            mime_type = str(asset.get("mime_type") or mime_type)
            size_bytes = asset.get("size_bytes")
        else:
            local_path = resolve_local_pdf_path(paper.get("pdf_path"))
            if local_path:
                filename = local_path.name
                size_bytes = local_path.stat().st_size
        return {
            "paper_id": paper_id,
            "title": paper.get("title"),
            "delivery": "reference",
            "mime_type": mime_type,
            "filename": filename or f"paper-{paper_id}.pdf",
            "size_bytes": size_bytes,
            "reference": reference,
        }

    if delivery != "base64":
        raise ValueError("delivery must be 'reference' or 'base64'.")

    data, filename, mime_type = _read_primary_pdf_bytes(paper_id, max_bytes=max_inline_bytes)
    return {
        "paper_id": paper_id,
        "title": paper.get("title"),
        "delivery": "base64",
        "mime_type": mime_type,
        "filename": filename,
        "size_bytes": len(data),
        "data_b64": base64.b64encode(data).decode("ascii"),
    }


def get_library_excerpt(
    paper_id: int,
    *,
    query: Optional[str] = None,
    page_no: Optional[int] = None,
    section_id: Optional[int] = None,
    max_chars: int = 4000,
    search_type: str = DEFAULT_TOOL_SEARCH_TYPE,
    limit: int = 5,
) -> Dict[str, Any]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    selectors = [bool(str(query or "").strip()), page_no is not None, section_id is not None]
    if sum(1 for item in selectors if item) != 1:
        raise ValueError("Provide exactly one of query, page_no, or section_id.")

    if query:
        q = str(query).strip()
        st = str(search_type or DEFAULT_TOOL_SEARCH_TYPE).strip().lower()
        if st not in {"keyword", "embedding", "hybrid"}:
            st = DEFAULT_TOOL_SEARCH_TYPE
        hits = search_paper_sections_for_localization(
            q,
            st,
            paper_id,
            keyword_section_hits_fn=_keyword_section_hits,
            semantic_section_hits_fn=_pgvector_search_section_hits,
            include_text=True,
            max_chars=max_chars,
            limit=max(3, limit),
            get_conn_fn=get_conn,
        )
        if not hits:
            return {
                "paper_id": paper_id,
                "title": paper.get("title"),
                "query": q,
                "hit_count": 0,
                "excerpt": None,
                "candidate_hits": [],
            }
        top = hits[0]
        candidate_hits = [
            {
                "section_id": int(hit.get("id") or 0),
                "page_no": int(hit.get("page_no") or 0),
                "section_canonical": hit.get("match_section_canonical"),
                "snippet": hit.get("match_text"),
                "bbox": hit.get("match_bbox"),
            }
            for hit in hits[:limit]
        ]
        return {
            "paper_id": paper_id,
            "title": paper.get("title"),
            "query": q,
            "hit_count": len(hits),
            "excerpt": {
                "section_id": int(top.get("id") or 0),
                "page_no": int(top.get("page_no") or 0),
                "section_canonical": top.get("match_section_canonical"),
                "snippet": top.get("match_text"),
                "bbox": top.get("match_bbox"),
                "text": str(top.get("text") or top.get("source_text") or "")[:max_chars],
            },
            "candidate_hits": candidate_hits,
        }

    with get_conn() as conn:
        if section_id is not None:
            row = conn.execute(
                """
                SELECT id, page_no, text
                FROM sections
                WHERE id = ? AND paper_id = ?
                """,
                (section_id, paper_id),
            ).fetchone()
            if not row:
                raise ValueError("Section not found for this paper.")
            text = str(row["text"] or "")
            return {
                "paper_id": paper_id,
                "title": paper.get("title"),
                "excerpt": {
                    "section_id": int(row["id"]),
                    "page_no": int(row["page_no"]),
                    "text": text[:max_chars],
                },
            }

        rows = conn.execute(
            """
            SELECT id, page_no, text
            FROM sections
            WHERE paper_id = ? AND page_no = ?
            ORDER BY id ASC
            """,
            (paper_id, int(page_no or 0)),
        ).fetchall()
    if not rows:
        raise ValueError("No text found for that page.")
    combined = "\n\n".join(str(row["text"] or "") for row in rows).strip()
    return {
        "paper_id": paper_id,
        "title": paper.get("title"),
        "excerpt": {
            "page_no": int(page_no or 0),
            "text": combined[:max_chars],
            "section_ids": [int(row["id"]) for row in rows],
        },
    }


def _fetch_text_blocks(paper_id: int) -> List[Any]:
    async def _run() -> List[Any]:
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
                return list(rows)
        finally:
            try:
                await close_pg_pool()
            except Exception:
                pass

    return run_async_blocking(_run)


def list_library_sections(paper_id: int) -> Dict[str, Any]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    rows = _fetch_text_blocks(paper_id)
    section_accumulator: Dict[str, Dict[str, Any]] = {}

    def _bucket(canonical: str) -> Dict[str, Any]:
        key = canonical or "other"
        existing = section_accumulator.get(key)
        if existing is None:
            existing = {
                "canonical": key,
                "chunk_count": 0,
                "pages": set(),
                "first_page": 10**9,
                "first_block_index": 10**9,
                "titles": set(),
                "source_counts": {},
                "confidence_sum": 0.0,
                "confidence_count": 0,
            }
            section_accumulator[key] = existing
        return existing

    for row in rows:
        metadata = _as_json_dict(row["metadata"])
        row_page = int(row["page_no"])
        row_block_index = int(row["block_index"])
        section_primary = str(metadata.get("section_primary") or "other").strip().lower() or "other"
        section_all = [str(item).strip().lower() for item in _as_json_list(metadata.get("section_all")) if str(item).strip()]
        section_titles = [str(item).strip() for item in _as_json_list(metadata.get("section_titles")) if str(item).strip()]
        section_source = str(metadata.get("section_source") or "unknown").strip() or "unknown"
        section_confidence = metadata.get("section_confidence")
        chunk_memberships: set[str] = set()

        block_items = _as_json_list(metadata.get("blocks"))
        for block in block_items:
            if not isinstance(block, dict):
                continue
            block_meta = block.get("metadata")
            block_meta = block_meta if isinstance(block_meta, dict) else {}
            canonical = str(block_meta.get("section_canonical") or section_primary or "other").strip().lower() or "other"
            page_no = int(block.get("page_no") or row_page)
            block_index = int(block.get("block_index") or 0)
            title = str(block_meta.get("section_title") or "").strip()
            if not title and section_titles:
                title = section_titles[0]
            source_name = str(block_meta.get("section_source") or section_source).strip() or "unknown"
            confidence = block_meta.get("section_confidence")
            if not isinstance(confidence, (int, float)):
                confidence = section_confidence

            bucket = _bucket(canonical)
            bucket["pages"].add(page_no)
            if page_no < bucket["first_page"] or (
                page_no == bucket["first_page"] and block_index < bucket["first_block_index"]
            ):
                bucket["first_page"] = page_no
                bucket["first_block_index"] = block_index
            if title:
                bucket["titles"].add(title)
            bucket["source_counts"][source_name] = bucket["source_counts"].get(source_name, 0) + 1
            if isinstance(confidence, (int, float)):
                bucket["confidence_sum"] += float(confidence)
                bucket["confidence_count"] += 1
            chunk_memberships.add(canonical)

        if not chunk_memberships:
            for canonical in section_all or [section_primary]:
                bucket = _bucket(canonical)
                bucket["pages"].add(row_page)
                if row_page < bucket["first_page"] or (
                    row_page == bucket["first_page"] and row_block_index < bucket["first_block_index"]
                ):
                    bucket["first_page"] = row_page
                    bucket["first_block_index"] = row_block_index
                for title in section_titles:
                    bucket["titles"].add(title)
                bucket["source_counts"][section_source] = bucket["source_counts"].get(section_source, 0) + 1
                if isinstance(section_confidence, (int, float)):
                    bucket["confidence_sum"] += float(section_confidence)
                    bucket["confidence_count"] += 1
                chunk_memberships.add(canonical)

        for canonical in chunk_memberships:
            _bucket(canonical)["chunk_count"] += 1

    sections = []
    for canonical, payload in section_accumulator.items():
        source_items = sorted(payload["source_counts"].items(), key=lambda item: item[1], reverse=True)
        avg_confidence = None
        if payload["confidence_count"] > 0:
            avg_confidence = round(payload["confidence_sum"] / payload["confidence_count"], 3)
        sections.append(
            {
                "canonical": canonical,
                "chunk_count": payload["chunk_count"],
                "pages": sorted(payload["pages"]),
                "first_page": payload["first_page"],
                "title_samples": sorted(payload["titles"])[:8],
                "primary_source": source_items[0][0] if source_items else "unknown",
                "avg_confidence": avg_confidence,
            }
        )

    sections.sort(key=lambda item: (item.get("first_page", 10**9), item.get("canonical", "")))
    return {
        "paper_id": paper_id,
        "title": paper.get("title"),
        "section_count": len(sections),
        "sections": sections,
    }


def get_library_section(
    paper_id: int,
    section_canonical: str,
    *,
    max_chars: int = 60000,
) -> Dict[str, Any]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    target = str(section_canonical or "").strip().lower()
    if not target:
        raise ValueError("section_canonical is required.")

    rows = _fetch_text_blocks(paper_id)
    source_blocks: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
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
            block_canonical = str(block_meta.get("section_canonical") or "").strip().lower() or section_primary
            if block_canonical != target:
                continue

            page_no = int(block.get("page_no") or row["page_no"])
            block_index = int(block.get("block_index") or 0)
            section_title = str(block_meta.get("section_title") or "").strip()
            section_source = str(block_meta.get("section_source") or metadata.get("section_source") or "unknown").strip() or "unknown"
            section_confidence = block_meta.get("section_confidence")
            block_bbox = _as_json_dict(block.get("bbox")) or None

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

    ordered_blocks = sorted(source_blocks.values(), key=lambda item: (item["page_no"], item["block_index"]))
    pages = sorted({item["page_no"] for item in ordered_blocks})
    full_text = "\n\n".join(item["text"] for item in ordered_blocks).strip()
    truncated = False
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars]
        truncated = True

    figure_manifest = paper_figures.load_paper_figure_manifest(paper_id)
    all_images = figure_manifest.get("images") or []
    section_images = _select_section_manifest_items(all_images, target=target, pages=pages)
    section_images = sorted(section_images, key=lambda item: (int(item.get("page_no") or 0), int(item.get("id") or 0)))

    equation_manifest = equation_extractor.load_paper_equation_manifest(paper_id)
    all_equations_raw = equation_manifest.get("equations") or []
    all_equations = all_equations_raw if isinstance(all_equations_raw, list) else []
    section_equations = _select_section_manifest_items(all_equations, target=target, pages=pages)
    section_equations = sorted(section_equations, key=lambda item: (int(item.get("page_no") or 0), int(item.get("id") or 0)))

    table_manifest = table_extractor.load_paper_table_manifest(paper_id)
    all_tables_raw = table_manifest.get("tables") or []
    all_tables = all_tables_raw if isinstance(all_tables_raw, list) else []
    section_tables = _select_section_manifest_items(all_tables, target=target, pages=pages)
    section_tables = sorted(section_tables, key=lambda item: (int(item.get("page_no") or 0), int(item.get("id") or 0)))

    return {
        "paper_id": paper_id,
        "title": paper.get("title"),
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
            for source, count in sorted(section_source_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "images": [_simplify_figure(item, paper_id=paper_id) for item in section_images if isinstance(item, dict)],
        "equations": [_simplify_equation(item, paper_id=paper_id) for item in section_equations if isinstance(item, dict)],
        "tables": [_simplify_table(item) for item in section_tables if isinstance(item, dict)],
    }


def list_library_figures(
    paper_id: int,
    *,
    section_canonical: Optional[str] = None,
    page_no: Optional[int] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    manifest = paper_figures.load_paper_figure_manifest(paper_id)
    images = manifest.get("images") or []
    if not isinstance(images, list):
        images = []
    if section_canonical:
        target = str(section_canonical).strip().lower()
        images = [item for item in images if str(item.get("section_canonical") or "").strip().lower() == target]
    if page_no is not None:
        images = [item for item in images if int(item.get("page_no") or 0) == int(page_no)]
    images = sorted(images, key=lambda item: (int(item.get("page_no") or 0), int(item.get("id") or 0)))
    return {
        "paper_id": paper_id,
        "title": paper.get("title"),
        "figure_count": len(images),
        "figures": [_simplify_figure(item, paper_id=paper_id) for item in images[:limit] if isinstance(item, dict)],
    }


def get_library_figure(
    paper_id: int,
    figure_name: str,
    *,
    delivery: str = "reference",
    max_inline_bytes: int = DEFAULT_INLINE_MAX_BYTES,
) -> Dict[str, Any]:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    name = Path(str(figure_name or "").strip()).name
    if not name:
        raise ValueError("figure_name is required.")

    manifest = paper_figures.load_paper_figure_manifest(paper_id)
    images = manifest.get("images") or []
    if not isinstance(images, list):
        images = []
    match = next((item for item in images if str(item.get("file_name") or "").strip() == name), None)
    reference = _api_reference(f"/api/papers/{paper_id}/figures/{quote(name)}")

    if delivery == "reference":
        payload: Dict[str, Any] = {
            "paper_id": paper_id,
            "title": paper.get("title"),
            "figure_name": name,
            "delivery": "reference",
            "reference": reference,
        }
        if isinstance(match, dict):
            payload.update(_simplify_figure(match, paper_id=paper_id))
        return payload

    if delivery != "base64":
        raise ValueError("delivery must be 'reference' or 'base64'.")

    data, filename, mime_type = _read_figure_bytes(paper_id, name, max_bytes=max_inline_bytes)
    payload = {
        "paper_id": paper_id,
        "title": paper.get("title"),
        "figure_name": filename,
        "delivery": "base64",
        "mime_type": mime_type,
        "size_bytes": len(data),
        "data_b64": base64.b64encode(data).decode("ascii"),
    }
    if isinstance(match, dict):
        payload["metadata"] = _simplify_figure(match, paper_id=paper_id)
    return payload


__all__ = [
    "find_library_papers",
    "get_library_pdf",
    "get_library_excerpt",
    "list_library_sections",
    "get_library_section",
    "list_library_figures",
    "get_library_figure",
    "load_library_paper_context",
]


def load_library_paper_context(
    paper_id: int,
    *,
    section_canonical: Optional[str] = None,
    max_chars: Optional[int] = None,
) -> QuestionContextUploadResponse:
    paper = _get_paper_row(paper_id)
    if not paper:
        raise ValueError("Paper not found.")

    limit = int(max_chars or os.getenv("QUESTION_CONTEXT_CHAR_LIMIT", "60000"))
    limit = max(1000, min(limit, 250000))

    if section_canonical:
        section_payload = get_library_section(paper_id, section_canonical, max_chars=limit)
        text = str(section_payload.get("full_text") or "").strip()
        label = str(section_payload.get("section_canonical") or section_canonical).strip()
        filename = f"{paper.get('title') or f'paper-{paper_id}'} [{label}]"
    else:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT text
                FROM sections
                WHERE paper_id = ?
                ORDER BY page_no ASC, id ASC
                """,
                (paper_id,),
            ).fetchall()
        text = "\n\n".join(str(row["text"] or "") for row in rows).strip()
        filename = str(paper.get("title") or f"paper-{paper_id}")

    if not text:
        raise ValueError("No text content is available for this paper.")
    if len(text) > limit:
        text = text[:limit]

    preview = text[:400].strip()
    return QuestionContextUploadResponse(
        context_id=uuid.uuid4().hex,
        filename=filename,
        characters=len(text),
        preview=preview,
        text=text,
    )
