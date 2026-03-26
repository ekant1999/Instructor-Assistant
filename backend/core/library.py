from __future__ import annotations

import asyncio
from collections import defaultdict
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import shutil
import threading

from .database import get_conn
from .search_cache import bump_search_index_version
from .pdf import describe_google_drive_source, resolve_any_to_pdf, extract_pages
from .storage import (
    delete_paper_assets,
    materialize_primary_pdf_path,
    paper_ids_with_primary_pdf_assets,
    upload_primary_pdf_asset,
)
from .web import extract_web_document, chunk_web_text
from .youtube_transcript import download_youtube_transcript, is_youtube_url

logger = logging.getLogger(__name__)


def _artifact_root(env_var: str, default_subdir: str) -> Path:
    configured = os.getenv(env_var, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / ".ia_phase1_data" / default_subdir).expanduser().resolve()


def _cleanup_local_paper_artifact_dirs(paper_id: int) -> List[str]:
    artifact_dirs = [
        _artifact_root("TABLE_OUTPUT_DIR", "tables") / str(int(paper_id)),
        _artifact_root("EQUATION_OUTPUT_DIR", "equations") / str(int(paper_id)),
        _artifact_root("FIGURE_OUTPUT_DIR", "figures") / str(int(paper_id)),
        _artifact_root("THUMBNAIL_OUTPUT_DIR", "thumbnails") / str(int(paper_id)),
        _artifact_root("MARKDOWN_OUTPUT_DIR", "markdown") / str(int(paper_id)),
    ]
    removed: List[str] = []
    for artifact_dir in artifact_dirs:
        if not artifact_dir.exists():
            continue
        try:
            shutil.rmtree(artifact_dir)
            removed.append(str(artifact_dir))
        except FileNotFoundError:
            continue
        except Exception:
            logger.exception("Failed to remove local artifact directory for paper %s: %s", paper_id, artifact_dir)
    return removed


async def add_paper(input_str: str, source_url: str | None = None, auto_index: bool = True) -> Dict[str, Any]:
    google_source = describe_google_drive_source(input_str)
    title, pdf_path = await resolve_any_to_pdf(input_str)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            (title, source_url or input_str, str(pdf_path)),
        )
        paper_id = c.lastrowid
        for page_no, text in extract_pages(pdf_path):
            c.execute(
                "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
                (paper_id, page_no, text),
            )
        conn.commit()
    try:
        upload_primary_pdf_asset(
            paper_id,
            pdf_path,
            source_kind=(google_source or {}).get("source_kind", "remote_pdf"),
            original_filename=Path(pdf_path).name,
            external_file_id=(google_source or {}).get("file_id"),
        )
    except Exception:
        with get_conn() as conn:
            conn.execute("DELETE FROM sections WHERE paper_id=?", (paper_id,))
            conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
            conn.commit()
        raise
    bump_search_index_version("add_paper")
    
    # Automatically trigger background reindexing for embedding search
    if auto_index:
        _trigger_background_reindex(paper_id, title)
    
    return {"paper_id": paper_id, "title": title, "pdf_path": str(pdf_path)}


async def add_web_page(url: str, source_url: str | None = None, auto_index: bool = True) -> Dict[str, Any]:
    title, text = await extract_web_document(url)
    chunk_size = int(os.getenv("WEB_CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("WEB_CHUNK_OVERLAP", "200"))
    chunks = chunk_web_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
    if not chunks:
        raise RuntimeError("No text could be extracted from the web page.")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            (title, source_url or url, ""),
        )
        paper_id = c.lastrowid
        for idx, chunk in enumerate(chunks, start=1):
            c.execute(
                "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
                (paper_id, idx, chunk),
            )
        conn.commit()
    bump_search_index_version("add_web_page")

    if auto_index:
        _trigger_background_reindex(paper_id, title)

    return {"paper_id": paper_id, "title": title, "pdf_path": "", "source_url": source_url or url}


async def add_youtube_transcript(
    video_url: str,
    source_url: str | None = None,
    auto_index: bool = True,
) -> Dict[str, Any]:
    if not is_youtube_url(video_url):
        raise RuntimeError("Invalid YouTube URL.")

    transcript = await asyncio.to_thread(download_youtube_transcript, video_url)
    title = str(transcript.get("title") or "YouTube Video").strip() or "YouTube Video"
    display_title = f"{title} (YouTube Transcript)"
    transcript_text = str(transcript.get("transcript_text") or "").strip()
    if not transcript_text:
        raise RuntimeError("No transcript text extracted from this YouTube URL.")

    chunk_size = int(os.getenv("YOUTUBE_CHUNK_SIZE", os.getenv("WEB_CHUNK_SIZE", "1000")))
    chunk_overlap = int(os.getenv("YOUTUBE_CHUNK_OVERLAP", os.getenv("WEB_CHUNK_OVERLAP", "200")))
    chunks = chunk_web_text(transcript_text, chunk_size=chunk_size, overlap=chunk_overlap)
    if not chunks:
        raise RuntimeError("Transcript extraction succeeded but produced no ingestible text chunks.")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            (display_title, source_url or video_url, ""),
        )
        paper_id = c.lastrowid
        for idx, chunk in enumerate(chunks, start=1):
            c.execute(
                "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
                (paper_id, idx, chunk),
            )
        conn.commit()
    bump_search_index_version("add_youtube_transcript")

    logger.info(
        "Added YouTube transcript paper_id=%s video_id=%s transcript_path=%s",
        paper_id,
        transcript.get("video_id"),
        transcript.get("transcript_path"),
    )

    if auto_index:
        _trigger_background_reindex(paper_id, display_title)

    return {
        "paper_id": paper_id,
        "title": display_title,
        "pdf_path": "",
        "source_url": source_url or video_url,
        "transcript_path": transcript.get("transcript_path"),
        "subtitle_path": transcript.get("subtitle_path"),
    }


def add_local_pdf(
    title: str | None,
    pdf_path: str | Path,
    source_url: str | None = None,
    auto_index: bool = True,
) -> Dict[str, Any]:
    path = Path(pdf_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF not found at {path}")
    final_title = title or path.stem
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            (final_title, source_url or str(path), str(path)),
        )
        paper_id = c.lastrowid
        for page_no, text in extract_pages(path):
            c.execute(
                "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
                (paper_id, page_no, text),
            )
        conn.commit()
    try:
        upload_primary_pdf_asset(
            paper_id,
            path,
            source_kind="local_pdf",
            original_filename=path.name,
        )
    except Exception:
        with get_conn() as conn:
            conn.execute("DELETE FROM sections WHERE paper_id=?", (paper_id,))
            conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
            conn.commit()
        raise
    bump_search_index_version("add_local_pdf")
    
    # Automatically trigger background reindexing for embedding search
    if auto_index:
        _trigger_background_reindex(paper_id, final_title)
    
    return {
        "paper_id": paper_id,
        "title": final_title,
        "pdf_path": str(path),
        "source_url": source_url or str(path),
    }


def delete_paper(paper_id: int, detach_notes: bool = False) -> Dict[str, Any]:
    delete_paper_assets(paper_id)
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        if detach_notes:
            conn.execute("UPDATE notes SET paper_id=NULL WHERE paper_id=?", (paper_id,))
        conn.execute("DELETE FROM sections WHERE paper_id=?", (paper_id,))
        conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
        if not detach_notes:
            conn.execute("DELETE FROM notes WHERE paper_id=?", (paper_id,))
        conn.execute("COMMIT")
    removed_artifact_dirs = _cleanup_local_paper_artifact_dirs(paper_id)
    bump_search_index_version("delete_paper")
    return {"deleted": True, "artifact_dirs_removed": removed_artifact_dirs}


def index_paper(paper_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT id, page_no FROM sections WHERE paper_id=? ORDER BY page_no ASC",
                (paper_id,),
            )
        ]
    return {"sections": rows}


def get_paper_chunk(section_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, paper_id, page_no, text FROM sections WHERE id=?",
            (section_id,),
        ).fetchone()
        if not row:
            raise ValueError("Section not found")
        return dict(row)


def save_note(paper_id: int, body: str, title: Optional[str] = None) -> Dict[str, Any]:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO notes(paper_id, body, title, created_at) VALUES(?,?,?, CURRENT_TIMESTAMP)",
            (paper_id, body, title),
        )
        conn.commit()
        note_id = c.lastrowid
    return {"note_id": note_id}


def _trigger_background_reindex(paper_id: int, paper_title: str):
    """
    Trigger background reindexing of a single paper for embedding search.
    Runs in a separate thread to avoid blocking the API response.
    """
    def reindex_paper():
        try:
            logger.info(f"📄 Starting background reindex for paper {paper_id}: {paper_title}")
            
            # Import here to avoid circular dependencies
            from ..rag import ingest_pgvector
            from ..core.postgres import get_pool, close_pool, normalize_timestamp

            # Get paper info
            with get_conn() as conn:
                row = conn.execute(
                    """
                    SELECT id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at
                    FROM papers
                    WHERE id=?
                    """,
                    (paper_id,),
                ).fetchone()
                if not row:
                    logger.error(f"Paper {paper_id} not found for reindexing")
                    return
                
                pdf_path = row["pdf_path"] or ""
                title = row["title"]
                source_url = row["source_url"]

            async def _reindex_async():
                try:
                    pool = await get_pool()
                    async with pool.acquire() as pg_conn:
                        await pg_conn.execute(
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
                            row["id"],
                            row["title"],
                            row["source_url"],
                            row["pdf_path"],
                            row["rag_status"],
                            row["rag_error"],
                        normalize_timestamp(row["rag_updated_at"]),
                        normalize_timestamp(row["created_at"]),
                    )

                    try:
                        with materialize_primary_pdf_path(paper_id, pdf_path) as resolved_pdf_path:
                            result = await ingest_pgvector.ingest_single_paper(
                                pdf_path=str(resolved_pdf_path),
                                paper_id=paper_id,
                                paper_title=title,
                                source_url=source_url,
                            )
                    except FileNotFoundError:
                        with get_conn() as conn:
                            section_rows = conn.execute(
                                "SELECT page_no, text FROM sections WHERE paper_id=? ORDER BY page_no ASC",
                                (paper_id,),
                            ).fetchall()
                        blocks = []
                        for section in section_rows:
                            text = (section["text"] or "").replace("\x00", "").strip()
                            if not text:
                                continue
                            blocks.append(
                                {
                                    "page_no": section["page_no"],
                                    "block_index": 0,
                                    "text": text,
                                    "bbox": None,
                                    "metadata": {
                                        "source_type": "web",
                                    "source_url": source_url,
                                    },
                                }
                            )
                        if not blocks:
                            raise RuntimeError("No text sections available for web document.")
                        result = await ingest_pgvector.ingest_blocks(
                            blocks=blocks,
                            paper_id=paper_id,
                            paper_title=title,
                        )

                    async with pool.acquire() as pg_conn:
                        await pg_conn.execute(
                            """
                        UPDATE papers
                        SET rag_status='done', rag_updated_at=NOW(), rag_error=NULL
                        WHERE id=$1
                        """,
                        paper_id,
                    )
                    return result
                finally:
                    await close_pool()

            result = asyncio.run(_reindex_async())
            
            # Update paper status
            with get_conn() as conn:
                conn.execute(
                    """UPDATE papers 
                       SET rag_status='done', rag_updated_at=CURRENT_TIMESTAMP 
                       WHERE id=?""",
                    (paper_id,)
                )
                conn.commit()
            bump_search_index_version("background_reindex_done")
            
            logger.info(f"✅ Background reindex completed for paper {paper_id}: {result['num_chunks']} chunks added")
            
        except Exception as e:
            logger.error(f"❌ Background reindex failed for paper {paper_id}: {e}")
            # Update paper status to show error
            try:
                with get_conn() as conn:
                    conn.execute(
                        """UPDATE papers 
                           SET rag_status='error', rag_error=?, rag_updated_at=CURRENT_TIMESTAMP 
                           WHERE id=?""",
                        (str(e)[:500], paper_id)
                    )
                    conn.commit()
                bump_search_index_version("background_reindex_error")
            except:
                pass
    
    # Start reindexing in background thread
    thread = threading.Thread(target=reindex_paper, daemon=True)
    thread.start()
    logger.info(f"⏳ Queued background reindex for paper {paper_id}: {paper_title}")


def render_library_structured() -> Dict[str, Any]:
    """Return the full library structure (papers + notes)."""
    with get_conn() as conn:
        paper_rows = conn.execute(
            """
            SELECT id, title, source_url, pdf_path, rag_status, rag_error, rag_updated_at, created_at
            FROM papers
            ORDER BY datetime(created_at) DESC, id DESC
        """
        ).fetchall()
        papers: List[Dict[str, Any]] = [dict(row) for row in paper_rows]
        asset_backed_papers = paper_ids_with_primary_pdf_assets(int(p["id"]) for p in papers)

        notes_stmt = conn.execute(
            "SELECT id, paper_id, title, body, created_at FROM notes ORDER BY created_at DESC"
        ).fetchall()

        notes_by_paper: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in notes_stmt:
            note = dict(row)
            paper_id = str(note["paper_id"])
            note["title"] = note.get("title") or (
                note["body"].splitlines()[0][:80] if note["body"] else "Note"
            )
            notes_by_paper[paper_id].append(note)

        for p in papers:
            key = str(p["id"])
            notes = notes_by_paper.get(key)
            if notes is None:
                notes = []
                notes_by_paper[key] = notes
            p["note_count"] = len(notes)
            pdf_path = p.get("pdf_path")
            has_pdf = bool(pdf_path) or int(p["id"]) in asset_backed_papers
            p["pdf_url"] = f"/papers/{p['id']}/file" if has_pdf else None

    return {"papers": papers, "notesByPaper": dict(notes_by_paper)}
