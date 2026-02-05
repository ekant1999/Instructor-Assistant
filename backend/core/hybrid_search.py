"""
Hybrid search combining pgvector similarity search with PostgreSQL full-text search.

Uses reciprocal rank fusion (RRF) to combine results from both methods.
"""
from typing import List, Dict, Any, Optional
import asyncpg
from backend.rag.pgvector_store import PgVectorStore


async def full_text_search(
    query: str,
    pool: asyncpg.Pool,
    k: int = 10,
    paper_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    PostgreSQL full-text search on text_blocks using tsvector.
    
    Args:
        query: Search query
        pool: asyncpg connection pool
        k: Number of results to return
        paper_ids: Optional list of paper IDs to filter by
    
    Returns:
        List of results with text, metadata, and relevance scores
    """
    # Build SQL query
    sql = """
        SELECT 
            tb.id,
            tb.paper_id,
            tb.page_no,
            tb.block_index,
            tb.text,
            tb.bbox,
            tb.metadata,
            p.title as paper_title,
            p.source_url,
            ts_rank(to_tsvector('english', tb.text), plainto_tsquery('english', $1)) as rank
        FROM text_blocks tb
        JOIN papers p ON tb.paper_id = p.id
        WHERE to_tsvector('english', tb.text) @@ plainto_tsquery('english', $1)
    """
    
    params = [query]
    param_idx = 2
    
    # Add paper_ids filter if provided
    if paper_ids:
        sql += f" AND tb.paper_id = ANY(${param_idx})"
        params.append(paper_ids)
        param_idx += 1
    
    # Order by rank and limit
    sql += f" ORDER BY rank DESC LIMIT ${param_idx}"
    params.append(k)
    
    # Execute query
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    
    # Format results
    results = []
    for row in rows:
        import json
        results.append({
            "id": row["id"],
            "paper_id": row["paper_id"],
            "page_no": row["page_no"],
            "block_index": row["block_index"],
            "text": row["text"],
            "bbox": json.loads(row["bbox"]) if row["bbox"] else None,
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            "paper_title": row["paper_title"],
            "source_url": row["source_url"],
            "score": float(row["rank"]),
            "source": "fts"
        })
    
    return results


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    fts_results: List[Dict[str, Any]],
    k: int = 10,
    alpha: float = 0.5,
    k_constant: int = 60
) -> List[Dict[str, Any]]:
    """
    Combine vector and FTS results using Reciprocal Rank Fusion (RRF).
    
    RRF formula: score = sum(1 / (k + rank_i)) for each result list
    
    Args:
        vector_results: Results from vector similarity search
        fts_results: Results from full-text search
        k: Number of final results to return
        alpha: Weight for vector search (0=FTS only, 1=vector only, 0.5=balanced)
        k_constant: RRF constant (typically 60)
    
    Returns:
        Fused and ranked results
    """
    # Create a mapping of block_id to result
    scores = {}
    result_map = {}
    
    # Process vector results
    for rank, result in enumerate(vector_results, start=1):
        block_id = result["id"]
        rrf_score = alpha / (k_constant + rank)
        
        if block_id not in scores:
            scores[block_id] = 0
            result_map[block_id] = result.copy()
            result_map[block_id]["sources"] = []
        
        scores[block_id] += rrf_score
        result_map[block_id]["sources"].append({
            "type": "vector",
            "rank": rank,
            "score": result.get("similarity", 0)
        })
    
    # Process FTS results
    for rank, result in enumerate(fts_results, start=1):
        block_id = result["id"]
        rrf_score = (1 - alpha) / (k_constant + rank)
        
        if block_id not in scores:
            scores[block_id] = 0
            result_map[block_id] = result.copy()
            result_map[block_id]["sources"] = []
        
        scores[block_id] += rrf_score
        result_map[block_id]["sources"].append({
            "type": "fts",
            "rank": rank,
            "score": result.get("score", 0)
        })
    
    # Sort by combined score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    # Build final results
    final_results = []
    for block_id in sorted_ids[:k]:
        result = result_map[block_id]
        result["hybrid_score"] = scores[block_id]
        final_results.append(result)
    
    return final_results


async def hybrid_search(
    query: str,
    pgvector_store: PgVectorStore,
    pool: asyncpg.Pool,
    k: int = 10,
    paper_ids: Optional[List[int]] = None,
    alpha: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Hybrid search combining vector similarity and full-text search.
    
    Args:
        query: Search query
        pgvector_store: PgVectorStore instance
        pool: asyncpg connection pool
        k: Number of final results to return
        paper_ids: Optional list of paper IDs to filter by
        alpha: Weight for vector search (0=FTS only, 1=vector only, 0.5=balanced)
    
    Returns:
        List of fused and ranked results
    """
    # Retrieve more results from each method to ensure good fusion
    retrieve_k = k * 2
    
    # Perform vector similarity search
    vector_results = await pgvector_store.similarity_search(
        query,
        k=retrieve_k,
        paper_ids=paper_ids
    )
    
    # Perform full-text search
    fts_results = await full_text_search(
        query,
        pool,
        k=retrieve_k,
        paper_ids=paper_ids
    )
    
    # Fuse results using RRF
    fused_results = reciprocal_rank_fusion(
        vector_results,
        fts_results,
        k=k,
        alpha=alpha
    )
    
    return fused_results


async def search_with_reranking(
    query: str,
    pgvector_store: PgVectorStore,
    pool: asyncpg.Pool,
    k: int = 10,
    paper_ids: Optional[List[int]] = None,
    alpha: float = 0.5,
    rerank_top_k: int = 50
) -> List[Dict[str, Any]]:
    """
    Hybrid search with optional reranking stage.
    
    This function is a placeholder for future cross-encoder reranking.
    Currently just performs hybrid search.
    
    Args:
        query: Search query
        pgvector_store: PgVectorStore instance
        pool: asyncpg connection pool
        k: Number of final results to return
        paper_ids: Optional list of paper IDs to filter by
        alpha: Weight for vector search
        rerank_top_k: Number of candidates to consider for reranking
    
    Returns:
        List of reranked results
    """
    # Get more candidates for reranking
    candidates = await hybrid_search(
        query,
        pgvector_store,
        pool,
        k=rerank_top_k,
        paper_ids=paper_ids,
        alpha=alpha
    )
    
    # TODO: Add cross-encoder reranking here
    # For now, just return top k from hybrid search
    return candidates[:k]
