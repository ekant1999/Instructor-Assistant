"""
pgvector-based query pipeline (replaces FAISS-based query.py).

Uses:
- pgvector for vector similarity search
- PostgreSQL full-text search
- Hybrid search with reciprocal rank fusion
"""
import os
import logging
from typing import Dict, Any, Optional, List, Literal

from core.postgres import get_pool
from core.hybrid_search import hybrid_search, full_text_search
from .pgvector_store import PgVectorStore
from .graph_pgvector import get_llm, generate_answer
from services import call_local_llm

logger = logging.getLogger(__name__)


async def query_rag(
    question: str,
    k: int = 6,
    paper_ids: Optional[List[int]] = None,
    provider: Optional[str] = None,
    search_type: Literal["keyword", "embedding", "hybrid"] = "hybrid",
    alpha: float = 0.5
) -> Dict[str, Any]:
    """
    Query the RAG system with pgvector.
    
    Args:
        question: The question to answer
        k: Number of results to retrieve
        paper_ids: Optional list of paper IDs to filter by
        provider: LLM provider ("openai" or "local")
        search_type: "keyword" (FTS), "embedding" (vector), or "hybrid" (both)
        alpha: Hybrid search weight (0=keyword only, 1=embedding only, 0.5=balanced)
    
    Returns:
        Dictionary with question, answer, context, and num_sources
    """
    pool = await get_pool()
    pgvector_store = PgVectorStore(pool)
    
    # Determine search method
    if search_type == "embedding":
        # Pure vector similarity search
        logger.info(f"Performing embedding search for: {question}")
        results = await pgvector_store.similarity_search(
            question,
            k=k,
            paper_ids=paper_ids
        )
    elif search_type == "keyword":
        # Pure full-text search
        logger.info(f"Performing keyword search for: {question}")
        results = await full_text_search(
            question,
            pool,
            k=k,
            paper_ids=paper_ids
        )
    else:  # hybrid
        # Hybrid search with RRF
        logger.info(f"Performing hybrid search for: {question}")
        results = await hybrid_search(
            question,
            pgvector_store,
            pool,
            k=k,
            paper_ids=paper_ids,
            alpha=alpha
        )
    
    if not results:
        reason = "No relevant content found for your query."
        if paper_ids:
            reason = "No relevant content found in the selected paper(s)."
        return {
            "question": question,
            "answer": reason,
            "context": [],
            "num_sources": 0
        }
    
    # Format context for LLM
    context = []
    for idx, result in enumerate(results, start=1):
        context.append({
            "text": result["text"],
            "meta": {
                "paper_id": result["paper_id"],
                "paper_title": result["paper_title"],
                "source": result.get("source_url", ""),
                "page_number": result["page_no"],
                "block_index": result["block_index"],
                "kind": "text",
            },
            "index": idx,
            "chunk_count": 1,
            "similarity": result.get("similarity"),
            "hybrid_score": result.get("hybrid_score")
        })
    
    # Generate answer
    resolved_provider = (provider or "openai").strip().lower()
    if resolved_provider not in {"openai", "local"}:
        resolved_provider = "openai"
    
    if resolved_provider == "local":
        # Use local LLM
        context_text = "\n\n".join([f"[{item['index']}] {item['text']}" for item in context])
        system_prompt = (
            "You are a helpful research assistant. Answer the question based ONLY on the provided context. "
            "Always include numbered citations [1], [2], etc. that correspond to the source numbers in the context. "
            "If information is not in the context, say so explicitly. "
            "Format your answer clearly with proper citations."
        )
        user_prompt = f"Context:\n\n{context_text}\n\nQuestion: {question}\n\nAnswer:"
        answer = call_local_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
    else:
        # Use OpenAI/ChatGPT
        llm = get_llm()
        answer = await generate_answer(question, context, llm)
    
    # Format response
    context_info = []
    for item in context:
        meta = item.get("meta", {}) or {}
        context_info.append({
            "paper": meta.get("paper_title") or meta.get("paper", "Unknown"),
            "source": meta.get("source", ""),
            "chunk_count": item.get("chunk_count", 0),
            "index": item.get("index", 0),
            "paper_id": meta.get("paper_id"),
            "paper_title": meta.get("paper_title"),
            "kind": meta.get("kind") or "text",
            "page_number": meta.get("page_number"),
            "block_index": meta.get("block_index"),
            "similarity": item.get("similarity"),
            "hybrid_score": item.get("hybrid_score")
        })
    
    return {
        "question": question,
        "answer": answer,
        "context": context_info,
        "num_sources": len(context_info)
    }


async def check_index_status() -> Dict[str, Any]:
    """Check pgvector index status."""
    try:
        pool = await get_pool()
        pgvector_store = PgVectorStore(pool)
        
        stats = await pgvector_store.get_index_stats()
        
        if stats["blocks_with_embeddings"] == 0:
            return {
                "exists": False,
                "message": "No embeddings found. Please run ingestion first."
            }
        
        return {
            "exists": True,
            "message": "pgvector index is ready",
            "stats": stats
        }
    except Exception as e:
        return {
            "exists": False,
            "message": f"Error checking index: {str(e)}"
        }
