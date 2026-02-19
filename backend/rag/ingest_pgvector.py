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
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from core.pdf import extract_text_blocks
from core.postgres import get_pool
from .chunking import chunk_text_blocks, simple_chunk_blocks
from .pgvector_store import PgVectorStore
from .section_extractor import annotate_blocks_with_sections
from .paper_figures import extract_and_store_paper_figures
from .table_extractor import extract_and_store_paper_tables, table_records_to_chunks

logger = logging.getLogger(__name__)


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
            logger.info(
                "  Extracted %s figures to dedicated folder",
                figure_report.get("num_images", 0),
            )
        except Exception as exc:
            # Figure extraction failure should not block text ingestion.
            logger.warning("  Figure extraction failed for paper %s: %s", paper_id, exc)

        table_report: Dict[str, Any] = {"num_tables": 0, "tables": []}
        table_chunks: List[Dict[str, Any]] = []
        try:
            table_report = extract_and_store_paper_tables(
                pdf_path=pdf_path_obj,
                paper_id=paper_id,
                blocks=blocks,
            )
            table_chunks = table_records_to_chunks(
                tables=table_report.get("tables") or [],
                text_blocks=blocks,
            )
            if table_chunks:
                logger.info(
                    "  Extracted %s tables and built %s table chunks",
                    table_report.get("num_tables", 0),
                    len(table_chunks),
                )
            elif table_report.get("num_tables", 0):
                logger.info("  Extracted %s tables", table_report.get("num_tables", 0))
        except Exception as exc:
            # Table extraction failure should not block text ingestion.
            logger.warning("  Table extraction failed for paper %s: %s", paper_id, exc)
        
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

    # Skip entries without a PDF path (e.g., web documents).
    papers = [p for p in papers if p.get("pdf_path")]
    if not papers:
        logger.warning("No PDF-backed papers found to ingest")
        return {"success": True, "papers_ingested": 0, "total_chunks": 0}
    
    logger.info(f"Ingesting {len(papers)} paper(s)...")
    
    # Ingest each paper
    total_chunks = 0
    failed = []
    
    for paper in papers:
        try:
            result = await ingest_single_paper(
                pdf_path=paper["pdf_path"],
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
