"""
pgvector-based ingestion pipeline (replaces FAISS-based ingest.py).

This ingests PDFs with:
- Block-level text extraction using PyMuPDF
- Smart chunking that respects block boundaries
- all-mpnet-base-v2 embeddings (768D)
- Storage in PostgreSQL with pgvector
"""
import os
import sys
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.pdf import extract_text_blocks
from core.postgres import get_pool
from core.storage import (
    delete_paper_assets_by_role,
    materialize_primary_pdf_path,
    object_storage_enabled,
    paper_ids_with_primary_pdf_assets,
    upload_paper_asset,
)
from .chunking import chunk_text_blocks, simple_chunk_blocks
from .markdown_exporter import MarkdownExportConfig, export_pdf_to_markdown
from .preview_assets import generate_and_store_paper_thumbnail
from .pgvector_store import PgVectorStore
from .section_extractor import annotate_blocks_with_sections
from .equation_extractor import extract_and_store_paper_equations, equation_records_to_chunks
from .paper_figures import extract_and_store_paper_figures, load_paper_figure_manifest
from .table_extractor import extract_and_store_paper_tables, table_records_to_chunks

logger = logging.getLogger(__name__)


def _load_manifest_json(manifest_path: str | Path) -> Dict[str, Any]:
    path = Path(manifest_path).expanduser()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _sync_figure_assets_from_manifest(paper_id: int, manifest_path: str | None = None) -> int:
    if not object_storage_enabled():
        return 0

    if manifest_path:
        manifest_file = Path(manifest_path).expanduser()
        manifest = _load_manifest_json(manifest_file) if manifest_file.exists() else load_paper_figure_manifest(paper_id)
    else:
        manifest = load_paper_figure_manifest(paper_id)
        manifest_file = Path(str(manifest.get("manifest_path") or "")).expanduser() if manifest.get("manifest_path") else None

    images = manifest.get("images") if isinstance(manifest, dict) else []
    image_records = images if isinstance(images, list) else []

    delete_paper_assets_by_role(paper_id, ["figure_image", "figure_manifest"])

    uploaded = 0
    manifest_changed = False
    for item in image_records:
        if not isinstance(item, dict):
            continue
        image_path_raw = str(item.get("image_path") or "").strip()
        if not image_path_raw:
            continue
        image_path = Path(image_path_raw).expanduser()
        if not image_path.exists():
            continue
        asset = upload_paper_asset(
            paper_id,
            image_path,
            role="figure_image",
            source_kind="derived_figure",
            original_filename=str(item.get("file_name") or image_path.name),
        )
        if asset is None:
            continue
        item["asset_storage_backend"] = asset.get("storage_backend")
        item["asset_bucket"] = asset.get("bucket")
        item["asset_object_key"] = asset.get("object_key")
        item["asset_role"] = "figure_image"
        uploaded += 1
        manifest_changed = True

    if manifest_changed and manifest_file and manifest_file.exists():
        with manifest_file.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)

    if manifest_file and manifest_file.exists():
        upload_paper_asset(
            paper_id,
            manifest_file,
            role="figure_manifest",
            source_kind="derived_manifest",
            original_filename="manifest.json",
            mime_type="application/json",
        )

    return uploaded


def _sync_equation_assets_from_manifest(paper_id: int, manifest_path: str | None = None) -> Dict[str, int]:
    if not object_storage_enabled():
        return {"images": 0, "json": 0}
    if not manifest_path:
        return {"images": 0, "json": 0}

    manifest_file = Path(manifest_path).expanduser()
    if not manifest_file.exists():
        return {"images": 0, "json": 0}

    manifest = _load_manifest_json(manifest_file)
    equations = manifest.get("equations")
    records = equations if isinstance(equations, list) else []

    delete_paper_assets_by_role(paper_id, ["equation_image", "equation_json", "equation_manifest"])
    uploaded_images = 0
    uploaded_json = 0

    for item in records:
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("file_name") or "").strip()
        image_path_raw = str(item.get("image_path") or "").strip()
        if file_name and image_path_raw:
            image_path = Path(image_path_raw).expanduser()
            if image_path.exists():
                upload_paper_asset(
                    paper_id,
                    image_path,
                    role="equation_image",
                    source_kind="derived_equation",
                    original_filename=file_name,
                )
                uploaded_images += 1

        json_name = str(item.get("json_file") or "").strip()
        if json_name:
            json_path = manifest_file.parent / json_name
            if json_path.exists():
                upload_paper_asset(
                    paper_id,
                    json_path,
                    role="equation_json",
                    source_kind="derived_equation",
                    original_filename=json_name,
                    mime_type="application/json",
                )
                uploaded_json += 1

    upload_paper_asset(
        paper_id,
        manifest_file,
        role="equation_manifest",
        source_kind="derived_manifest",
        original_filename="manifest.json",
        mime_type="application/json",
    )
    return {"images": uploaded_images, "json": uploaded_json}


def _sync_table_assets_from_manifest(paper_id: int, manifest_path: str | None = None) -> Dict[str, int]:
    if not object_storage_enabled():
        return {"json": 0}
    if not manifest_path:
        return {"json": 0}

    manifest_file = Path(manifest_path).expanduser()
    if not manifest_file.exists():
        return {"json": 0}

    manifest = _load_manifest_json(manifest_file)
    tables = manifest.get("tables")
    records = tables if isinstance(tables, list) else []

    delete_paper_assets_by_role(paper_id, ["table_json", "table_manifest"])
    uploaded_json = 0

    for item in records:
        if not isinstance(item, dict):
            continue
        json_name = str(item.get("json_file") or "").strip()
        if not json_name:
            continue
        json_path = manifest_file.parent / json_name
        if not json_path.exists():
            continue
        upload_paper_asset(
            paper_id,
            json_path,
            role="table_json",
            source_kind="derived_table",
            original_filename=json_name,
            mime_type="application/json",
        )
        uploaded_json += 1

    upload_paper_asset(
        paper_id,
        manifest_file,
        role="table_manifest",
        source_kind="derived_manifest",
        original_filename="manifest.json",
        mime_type="application/json",
    )
    return {"json": uploaded_json}


def _sync_thumbnail_asset(paper_id: int, thumbnail_path: Path | None) -> int:
    if not object_storage_enabled() or thumbnail_path is None or not thumbnail_path.exists():
        return 0
    delete_paper_assets_by_role(paper_id, ["paper_thumbnail"])
    asset = upload_paper_asset(
        paper_id,
        thumbnail_path,
        role="paper_thumbnail",
        source_kind="derived_thumbnail",
        original_filename=thumbnail_path.name,
    )
    return 1 if asset is not None else 0


def _sync_markdown_bundle_assets(
    paper_id: int,
    *,
    markdown_path: str | Path | None,
    manifest_path: str | Path | None,
) -> Dict[str, int]:
    if not object_storage_enabled():
        return {"markdown": 0, "manifest": 0}

    delete_paper_assets_by_role(paper_id, ["paper_markdown", "paper_markdown_manifest"])
    uploaded = {"markdown": 0, "manifest": 0}

    if markdown_path:
        markdown_file = Path(markdown_path).expanduser()
        if markdown_file.exists():
            asset = upload_paper_asset(
                paper_id,
                markdown_file,
                role="paper_markdown",
                source_kind="derived_markdown",
                original_filename=markdown_file.name,
                mime_type="text/markdown",
            )
            if asset is not None:
                uploaded["markdown"] = 1

    if manifest_path:
        manifest_file = Path(manifest_path).expanduser()
        if manifest_file.exists():
            asset = upload_paper_asset(
                paper_id,
                manifest_file,
                role="paper_markdown_manifest",
                source_kind="derived_manifest",
                original_filename=manifest_file.name,
                mime_type="application/json",
            )
            if asset is not None:
                uploaded["manifest"] = 1

    return uploaded


async def ingest_single_paper(
    pdf_path: str,
    paper_id: int,
    paper_title: str,
    source_url: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    use_simple_chunking: bool = False
) -> Dict[str, Any]:
    """
    Ingest a single paper into pgvector.
    
    Args:
        pdf_path: Path to the PDF file
        paper_id: Database ID of the paper
        paper_title: Title of the paper
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        use_simple_chunking: Use simple block combining instead of smart chunking
    
    Returns:
        Dictionary with ingestion results
    """
    try:
        logger.info(f"Ingesting paper {paper_id}: {paper_title}")
        
        # Extract text blocks with PyMuPDF
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise ValueError(f"PDF not found: {pdf_path}")
        
        logger.info("  Extracting text blocks...")
        blocks = extract_text_blocks(pdf_path_obj)
        logger.info(f"  Extracted {len(blocks)} text blocks")
        
        if not blocks:
            raise ValueError("No text blocks extracted from PDF")

        section_report = annotate_blocks_with_sections(
            blocks,
            pdf_path_obj,
            source_url=source_url,
        )
        logger.info(
            "  Section extraction strategy=%s, sections=%s",
            section_report.get("strategy"),
            len(section_report.get("sections") or []),
        )

        figure_report: Dict[str, Any] = {"num_images": 0}
        try:
            figure_report = extract_and_store_paper_figures(
                pdf_path=pdf_path_obj,
                paper_id=paper_id,
                blocks=blocks,
            )
            uploaded_figure_assets = _sync_figure_assets_from_manifest(
                paper_id,
                figure_report.get("manifest_path"),
            )
            logger.info(
                "  Extracted %s figures to dedicated folder (%s synced to object storage)",
                figure_report.get("num_images", 0),
                uploaded_figure_assets,
            )
        except Exception as exc:
            # Figure extraction failure should not block text ingestion.
            logger.warning("  Figure extraction failed for paper %s: %s", paper_id, exc)

        table_report: Dict[str, Any] = {"num_tables": 0, "tables": []}
        table_chunks: List[Dict[str, Any]] = []
        table_asset_report: Dict[str, int] = {"json": 0}
        try:
            table_report = extract_and_store_paper_tables(
                pdf_path=pdf_path_obj,
                paper_id=paper_id,
                blocks=blocks,
            )
            table_asset_report = _sync_table_assets_from_manifest(
                paper_id,
                table_report.get("manifest_path"),
            )
            table_chunks = table_records_to_chunks(
                tables=table_report.get("tables") or [],
                text_blocks=blocks,
            )
            if table_chunks:
                logger.info(
                    "  Extracted %s tables, built %s table chunks, synced %s table JSON assets",
                    table_report.get("num_tables", 0),
                    len(table_chunks),
                    table_asset_report.get("json", 0),
                )
            elif table_report.get("num_tables", 0):
                logger.info(
                    "  Extracted %s tables and synced %s table JSON assets",
                    table_report.get("num_tables", 0),
                    table_asset_report.get("json", 0),
                )
        except Exception as exc:
            # Table extraction failure should not block text ingestion.
            logger.warning("  Table extraction failed for paper %s: %s", paper_id, exc)

        equation_report: Dict[str, Any] = {"num_equations": 0, "equations": []}
        equation_chunks: List[Dict[str, Any]] = []
        equation_asset_report: Dict[str, int] = {"images": 0, "json": 0}
        try:
            equation_report = extract_and_store_paper_equations(
                pdf_path=pdf_path_obj,
                paper_id=paper_id,
                blocks=blocks,
            )
            equation_asset_report = _sync_equation_assets_from_manifest(
                paper_id,
                equation_report.get("manifest_path"),
            )
            equation_chunks = equation_records_to_chunks(
                equations=equation_report.get("equations") or [],
                text_blocks=blocks,
            )
            if equation_chunks:
                logger.info(
                    "  Extracted %s equations, built %s equation chunks, synced %s equation images and %s JSON assets",
                    equation_report.get("num_equations", 0),
                    len(equation_chunks),
                    equation_asset_report.get("images", 0),
                    equation_asset_report.get("json", 0),
                )
            elif equation_report.get("num_equations", 0):
                logger.info(
                    "  Extracted %s equations and synced %s equation images and %s JSON assets",
                    equation_report.get("num_equations", 0),
                    equation_asset_report.get("images", 0),
                    equation_asset_report.get("json", 0),
                )
        except Exception as exc:
            # Equation extraction failure should not block text ingestion.
            logger.warning("  Equation extraction failed for paper %s: %s", paper_id, exc)

        thumbnail_report: Dict[str, Any] = {"thumbnail_path": None}
        thumbnail_uploaded = 0
        try:
            thumbnail_report = generate_and_store_paper_thumbnail(
                pdf_path=pdf_path_obj,
                paper_id=paper_id,
            )
            thumbnail_uploaded = _sync_thumbnail_asset(
                paper_id,
                Path(str(thumbnail_report.get("thumbnail_path"))).expanduser()
                if thumbnail_report.get("thumbnail_path")
                else None,
            )
            logger.info("  Generated thumbnail (%s synced to object storage)", thumbnail_uploaded)
        except Exception as exc:
            logger.warning("  Thumbnail generation failed for paper %s: %s", paper_id, exc)

        markdown_export_result: Optional[Dict[str, Any]] = None
        markdown_asset_report: Dict[str, int] = {"markdown": 0, "manifest": 0}
        try:
            markdown_result = export_pdf_to_markdown(
                pdf_path_obj,
                paper_id=paper_id,
                source_url=source_url,
                metadata={"title": paper_title},
                blocks=blocks,
                config=MarkdownExportConfig(
                    ensure_assets=False,
                    asset_mode="copy",
                    asset_path_mode="relative",
                    include_frontmatter=True,
                    include_page_markers=False,
                    overwrite=True,
                ),
            )
            markdown_export_result = {
                "bundle_dir": str(markdown_result.bundle_dir),
                "markdown_path": str(markdown_result.markdown_path),
                "manifest_path": str(markdown_result.manifest_path),
                "asset_counts": dict(markdown_result.asset_counts),
            }
            markdown_asset_report = _sync_markdown_bundle_assets(
                paper_id,
                markdown_path=markdown_result.markdown_path,
                manifest_path=markdown_result.manifest_path,
            )
            logger.info(
                "  Generated markdown bundle at %s (%s markdown, %s manifest synced to object storage)",
                markdown_result.bundle_dir,
                markdown_asset_report.get("markdown", 0),
                markdown_asset_report.get("manifest", 0),
            )
        except Exception as exc:
            logger.warning("  Markdown export failed for paper %s: %s", paper_id, exc)
        
        # Chunk the blocks
        logger.info("  Chunking blocks...")
        if use_simple_chunking:
            chunks = simple_chunk_blocks(blocks, max_chars=chunk_size)
        else:
            chunks = chunk_text_blocks(
                blocks,
                target_size=chunk_size,
                overlap=chunk_overlap
            )
        if table_chunks:
            chunks.extend(table_chunks)
        if equation_chunks:
            chunks.extend(equation_chunks)
        logger.info(f"  Created {len(chunks)} chunks")
        
        # Get pgvector store
        pool = await get_pool()
        pgvector_store = PgVectorStore(pool)
        
        # Delete existing blocks for this paper (if any)
        deleted = await pgvector_store.delete_paper_blocks(paper_id)
        if deleted > 0:
            logger.info(f"  Deleted {deleted} existing blocks")
        
        # Insert chunks with embeddings
        logger.info("  Generating embeddings and inserting...")
        inserted = await pgvector_store.insert_blocks(chunks, paper_id)
        logger.info(f"  ✓ Inserted {inserted} blocks with embeddings")
        
        return {
            "success": True,
            "paper_id": paper_id,
            "num_blocks": len(blocks),
            "num_chunks": len(chunks),
            "num_inserted": inserted,
            "section_strategy": section_report.get("strategy"),
            "num_sections": len(section_report.get("sections") or []),
            "num_figures": figure_report.get("num_images", 0),
            "num_tables": table_report.get("num_tables", 0),
            "num_table_chunks": len(table_chunks),
            "num_equations": equation_report.get("num_equations", 0),
            "num_equation_chunks": len(equation_chunks),
            "thumbnail_uploaded": thumbnail_uploaded,
            "markdown_bundle_dir": (markdown_export_result or {}).get("bundle_dir"),
            "markdown_path": (markdown_export_result or {}).get("markdown_path"),
            "markdown_asset_counts": (markdown_export_result or {}).get("asset_counts", {}),
            "markdown_uploaded": markdown_asset_report.get("markdown", 0),
            "markdown_manifest_uploaded": markdown_asset_report.get("manifest", 0),
        }
    
    except Exception as e:
        logger.error(f"Failed to ingest paper {paper_id}: {e}")
        raise


async def ingest_blocks(
    blocks: List[Dict[str, Any]],
    paper_id: int,
    paper_title: str,
) -> Dict[str, Any]:
    """
    Ingest pre-built text blocks (e.g., from web pages) into pgvector.
    """
    if not blocks:
        raise ValueError("No blocks provided for ingestion.")
    try:
        pool = await get_pool()
        pgvector_store = PgVectorStore(pool)

        deleted = await pgvector_store.delete_paper_blocks(paper_id)
        if deleted > 0:
            logger.info("  Deleted %s existing blocks", deleted)

        inserted = await pgvector_store.insert_blocks(blocks, paper_id)
        logger.info("  ✓ Inserted %s blocks with embeddings", inserted)

        return {
            "success": True,
            "paper_id": paper_id,
            "paper_title": paper_title,
            "num_blocks": len(blocks),
            "num_chunks": len(blocks),
            "num_inserted": inserted,
        }
    except Exception as e:
        logger.error("Failed to ingest blocks for paper %s: %s", paper_id, e)
        raise


async def ingest_papers_from_db(
    paper_ids: Optional[List[int]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict[str, Any]:
    """
    Ingest papers from the database into pgvector.
    
    Args:
        paper_ids: Optional list of paper IDs to ingest (None = all papers)
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
    
    Returns:
        Summary of ingestion results
    """
    pool = await get_pool()
    
    # Get papers to ingest
    async with pool.acquire() as conn:
        if paper_ids:
            papers = await conn.fetch(
                "SELECT id, title, source_url, pdf_path FROM papers WHERE id = ANY($1) ORDER BY id",
                paper_ids
            )
        else:
            papers = await conn.fetch(
                "SELECT id, title, source_url, pdf_path FROM papers ORDER BY id"
            )
    
    if not papers:
        logger.warning("No papers found to ingest")
        return {"success": True, "papers_ingested": 0, "total_chunks": 0}

    asset_backed_ids = paper_ids_with_primary_pdf_assets(int(p["id"]) for p in papers)
    # Skip entries without any resolvable PDF source (e.g., web documents).
    papers = [p for p in papers if p.get("pdf_path") or int(p["id"]) in asset_backed_ids]
    if not papers:
        logger.warning("No PDF-backed papers found to ingest")
        return {"success": True, "papers_ingested": 0, "total_chunks": 0}
    
    logger.info(f"Ingesting {len(papers)} paper(s)...")
    
    # Ingest each paper
    total_chunks = 0
    failed = []
    
    for paper in papers:
        try:
            with materialize_primary_pdf_path(int(paper["id"]), paper.get("pdf_path")) as resolved_pdf_path:
                result = await ingest_single_paper(
                    pdf_path=str(resolved_pdf_path),
                    paper_id=paper["id"],
                    paper_title=paper["title"] or "Untitled",
                    source_url=paper.get("source_url"),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            total_chunks += result["num_chunks"]
        except Exception as e:
            logger.error(f"Failed to ingest paper {paper['id']}: {e}")
            failed.append({
                "paper_id": paper["id"],
                "title": paper["title"],
                "error": str(e)
            })
    
    # Update rag_status for papers
    async with pool.acquire() as conn:
        if paper_ids:
            await conn.execute(
                """
                UPDATE papers 
                SET rag_status = 'done', 
                    rag_updated_at = NOW(),
                    rag_error = NULL
                WHERE id = ANY($1)
                """,
                paper_ids
            )
    
    logger.info(f"✓ Ingestion complete: {len(papers) - len(failed)}/{len(papers)} succeeded")
    
    return {
        "success": len(failed) == 0,
        "papers_ingested": len(papers) - len(failed),
        "total_papers": len(papers),
        "total_chunks": total_chunks,
        "failed": failed
    }


async def reindex_all_papers(
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict[str, Any]:
    """
    Re-index all papers in the database.
    
    This is useful after:
    - Migrating from SQLite to PostgreSQL
    - Changing embedding models
    - Updating chunking strategy
    
    Args:
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
    
    Returns:
        Summary of reindexing results
    """
    logger.info("=" * 60)
    logger.info("Reindexing all papers with pgvector")
    logger.info("=" * 60)
    
    result = await ingest_papers_from_db(
        paper_ids=None,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    logger.info("=" * 60)
    logger.info("Reindexing complete!")
    logger.info(f"Papers: {result['papers_ingested']}/{result['total_papers']}")
    logger.info(f"Total chunks: {result['total_chunks']}")
    logger.info("=" * 60)
    
    return result


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(reindex_all_papers())
