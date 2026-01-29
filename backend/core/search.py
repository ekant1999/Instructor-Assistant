"""
Hybrid search service combining keyword-based (FTS5) and embedding-based (FAISS) search.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from .database import get_conn


SearchType = Literal["keyword", "embedding", "hybrid"]


def search_papers(
    query: str,
    search_type: SearchType = "keyword",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search papers using keyword-based (FTS5) or hybrid search.
    
    Args:
        query: Search query string
        search_type: "keyword", "embedding", or "hybrid"
        limit: Maximum number of results to return
    
    Returns:
        List of paper dictionaries with relevance scores
    """
    if search_type == "embedding":
        # For embedding-only search, we'd need to create embeddings for paper titles
        # For now, fall back to keyword search
        search_type = "keyword"
    
    if search_type in ["keyword", "hybrid"]:
        with get_conn() as conn:
            # Escape FTS5 query and wrap in quotes for phrase search
            # This handles special characters and multi-word queries
            fts_query = f'"{query}"' if ' ' in query or '-' in query else query
            
            try:
                # Use FTS5 MATCH for full-text search
                results = conn.execute(
                    """
                    SELECT p.id, p.title, p.source_url, p.pdf_path, p.rag_status, 
                           p.rag_error, p.rag_updated_at, p.created_at,
                           pf.rank
                    FROM papers p
                    JOIN papers_fts pf ON p.id = pf.rowid
                    WHERE papers_fts MATCH ?
                    ORDER BY pf.rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                ).fetchall()
                
                return [dict(row) for row in results]
            except Exception as e:
                # If FTS5 query fails, fall back to simple LIKE search
                print(f"FTS5 search failed, falling back to LIKE: {e}")
                results = conn.execute(
                    """
                    SELECT id, title, source_url, pdf_path, rag_status, 
                           rag_error, rag_updated_at, created_at,
                           0 as rank
                    FROM papers
                    WHERE title LIKE ? OR source_url LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
                
                return [dict(row) for row in results]
    
    return []


def search_sections(
    query: str,
    search_type: SearchType = "keyword",
    paper_ids: Optional[List[int]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search PDF sections (pages) using keyword-based FTS5 search.
    
    Args:
        query: Search query string
        search_type: "keyword", "embedding", or "hybrid"
        paper_ids: Optional list of paper IDs to filter by
        limit: Maximum number of results to return
    
    Returns:
        List of section dictionaries with paper info and relevance scores
    """
    if search_type == "embedding":
        # Embedding search for sections should use the RAG system
        # This is handled separately in the RAG query function
        return []
    
    if search_type in ["keyword", "hybrid"]:
        with get_conn() as conn:
            # Escape FTS5 query and wrap in quotes for phrase search
            fts_query = f'"{query}"' if ' ' in query or '-' in query else query
            
            try:
                if paper_ids:
                    placeholders = ",".join("?" * len(paper_ids))
                    query_sql = f"""
                        SELECT s.id, s.paper_id, s.page_no, s.text,
                               p.title as paper_title, p.source_url,
                               sf.rank
                        FROM sections s
                        JOIN sections_fts sf ON s.id = sf.rowid
                        JOIN papers p ON s.paper_id = p.id
                        WHERE sections_fts MATCH ? AND s.paper_id IN ({placeholders})
                        ORDER BY sf.rank
                        LIMIT ?
                    """
                    params = [fts_query] + paper_ids + [limit]
                else:
                    query_sql = """
                        SELECT s.id, s.paper_id, s.page_no, s.text,
                               p.title as paper_title, p.source_url,
                               sf.rank
                        FROM sections s
                        JOIN sections_fts sf ON s.id = sf.rowid
                        JOIN papers p ON s.paper_id = p.id
                        WHERE sections_fts MATCH ?
                        ORDER BY sf.rank
                        LIMIT ?
                    """
                    params = [fts_query, limit]
                
                results = conn.execute(query_sql, params).fetchall()
                return [dict(row) for row in results]
            except Exception as e:
                # If FTS5 query fails, fall back to LIKE search
                print(f"FTS5 search failed, falling back to LIKE: {e}")
                if paper_ids:
                    placeholders = ",".join("?" * len(paper_ids))
                    query_sql = f"""
                        SELECT s.id, s.paper_id, s.page_no, s.text,
                               p.title as paper_title, p.source_url,
                               0 as rank
                        FROM sections s
                        JOIN papers p ON s.paper_id = p.id
                        WHERE s.text LIKE ? AND s.paper_id IN ({placeholders})
                        ORDER BY s.page_no
                        LIMIT ?
                    """
                    params = [f"%{query}%"] + paper_ids + [limit]
                else:
                    query_sql = """
                        SELECT s.id, s.paper_id, s.page_no, s.text,
                               p.title as paper_title, p.source_url,
                               0 as rank
                        FROM sections s
                        JOIN papers p ON s.paper_id = p.id
                        WHERE s.text LIKE ?
                        ORDER BY s.page_no
                        LIMIT ?
                    """
                    params = [f"%{query}%", limit]
                
                results = conn.execute(query_sql, params).fetchall()
                return [dict(row) for row in results]
    
    return []


def search_notes(
    query: str,
    search_type: SearchType = "keyword",
    paper_ids: Optional[List[int]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search notes using keyword-based FTS5 search.
    
    Args:
        query: Search query string
        search_type: "keyword", "embedding", or "hybrid"
        paper_ids: Optional list of paper IDs to filter by
        limit: Maximum number of results to return
    
    Returns:
        List of note dictionaries with relevance scores
    """
    if search_type == "embedding":
        # For embedding-only search on notes, fall back to keyword
        search_type = "keyword"
    
    if search_type in ["keyword", "hybrid"]:
        with get_conn() as conn:
            # Escape FTS5 query
            fts_query = f'"{query}"' if ' ' in query or '-' in query else query
            
            try:
                if paper_ids:
                    placeholders = ",".join("?" * len(paper_ids))
                    query_sql = f"""
                        SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                               p.title as paper_title,
                               nf.rank
                        FROM notes n
                        JOIN notes_fts nf ON n.id = nf.rowid
                        LEFT JOIN papers p ON n.paper_id = p.id
                        WHERE notes_fts MATCH ? AND (n.paper_id IN ({placeholders}) OR n.paper_id IS NULL)
                        ORDER BY nf.rank
                        LIMIT ?
                    """
                    params = [fts_query] + paper_ids + [limit]
                else:
                    query_sql = """
                        SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                               p.title as paper_title,
                               nf.rank
                        FROM notes n
                        JOIN notes_fts nf ON n.id = nf.rowid
                        LEFT JOIN papers p ON n.paper_id = p.id
                        WHERE notes_fts MATCH ?
                        ORDER BY nf.rank
                        LIMIT ?
                    """
                    params = [fts_query, limit]
                
                results = conn.execute(query_sql, params).fetchall()
                return [dict(row) for row in results]
            except Exception as e:
                # Fall back to LIKE search
                print(f"FTS5 search failed, falling back to LIKE: {e}")
                if paper_ids:
                    placeholders = ",".join("?" * len(paper_ids))
                    query_sql = f"""
                        SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                               p.title as paper_title,
                               0 as rank
                        FROM notes n
                        LEFT JOIN papers p ON n.paper_id = p.id
                        WHERE (n.title LIKE ? OR n.body LIKE ?) 
                              AND (n.paper_id IN ({placeholders}) OR n.paper_id IS NULL)
                        ORDER BY n.created_at DESC
                        LIMIT ?
                    """
                    params = [f"%{query}%", f"%{query}%"] + paper_ids + [limit]
                else:
                    query_sql = """
                        SELECT n.id, n.paper_id, n.title, n.body, n.tags_json, n.created_at,
                               p.title as paper_title,
                               0 as rank
                        FROM notes n
                        LEFT JOIN papers p ON n.paper_id = p.id
                        WHERE n.title LIKE ? OR n.body LIKE ?
                        ORDER BY n.created_at DESC
                        LIMIT ?
                    """
                    params = [f"%{query}%", f"%{query}%", limit]
                
                results = conn.execute(query_sql, params).fetchall()
                return [dict(row) for row in results]
    
    return []


def search_summaries(
    query: str,
    search_type: SearchType = "keyword",
    paper_ids: Optional[List[int]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search summaries using keyword-based FTS5 search.
    
    Args:
        query: Search query string
        search_type: "keyword", "embedding", or "hybrid"
        paper_ids: Optional list of paper IDs to filter by
        limit: Maximum number of results to return
    
    Returns:
        List of summary dictionaries with relevance scores
    """
    if search_type == "embedding":
        # For embedding-only search on summaries, fall back to keyword
        search_type = "keyword"
    
    if search_type in ["keyword", "hybrid"]:
        with get_conn() as conn:
            # Escape FTS5 query
            fts_query = f'"{query}"' if ' ' in query or '-' in query else query
            
            try:
                if paper_ids:
                    placeholders = ",".join("?" * len(paper_ids))
                    query_sql = f"""
                        SELECT s.id, s.paper_id, s.title, s.content, s.agent, s.style,
                               s.word_count, s.is_edited, s.metadata_json, s.created_at, s.updated_at,
                               p.title as paper_title,
                               sf.rank
                        FROM summaries s
                        JOIN summaries_fts sf ON s.id = sf.rowid
                        JOIN papers p ON s.paper_id = p.id
                        WHERE summaries_fts MATCH ? AND s.paper_id IN ({placeholders})
                        ORDER BY sf.rank
                        LIMIT ?
                    """
                    params = [fts_query] + paper_ids + [limit]
                else:
                    query_sql = """
                        SELECT s.id, s.paper_id, s.title, s.content, s.agent, s.style,
                               s.word_count, s.is_edited, s.metadata_json, s.created_at, s.updated_at,
                               p.title as paper_title,
                               sf.rank
                        FROM summaries s
                        JOIN summaries_fts sf ON s.id = sf.rowid
                        JOIN papers p ON s.paper_id = p.id
                        WHERE summaries_fts MATCH ?
                        ORDER BY sf.rank
                        LIMIT ?
                    """
                    params = [fts_query, limit]
                
                results = conn.execute(query_sql, params).fetchall()
                return [dict(row) for row in results]
            except Exception as e:
                # Fall back to LIKE search
                print(f"FTS5 search failed, falling back to LIKE: {e}")
                if paper_ids:
                    placeholders = ",".join("?" * len(paper_ids))
                    query_sql = f"""
                        SELECT s.id, s.paper_id, s.title, s.content, s.agent, s.style,
                               s.word_count, s.is_edited, s.metadata_json, s.created_at, s.updated_at,
                               p.title as paper_title,
                               0 as rank
                        FROM summaries s
                        JOIN papers p ON s.paper_id = p.id
                        WHERE (s.title LIKE ? OR s.content LIKE ?) AND s.paper_id IN ({placeholders})
                        ORDER BY s.created_at DESC
                        LIMIT ?
                    """
                    params = [f"%{query}%", f"%{query}%"] + paper_ids + [limit]
                else:
                    query_sql = """
                        SELECT s.id, s.paper_id, s.title, s.content, s.agent, s.style,
                               s.word_count, s.is_edited, s.metadata_json, s.created_at, s.updated_at,
                               p.title as paper_title,
                               0 as rank
                        FROM summaries s
                        JOIN papers p ON s.paper_id = p.id
                        WHERE s.title LIKE ? OR s.content LIKE ?
                        ORDER BY s.created_at DESC
                        LIMIT ?
                    """
                    params = [f"%{query}%", f"%{query}%", limit]
                
                results = conn.execute(query_sql, params).fetchall()
                return [dict(row) for row in results]
    
    return []


def search_all(
    query: str,
    search_type: SearchType = "keyword",
    paper_ids: Optional[List[int]] = None,
    limit_per_category: int = 10,
) -> Dict[str, Any]:
    """
    Search across all categories (papers, sections, notes, summaries).
    
    Args:
        query: Search query string
        search_type: "keyword", "embedding", or "hybrid"
        paper_ids: Optional list of paper IDs to filter by
        limit_per_category: Maximum results per category
    
    Returns:
        Dictionary with results for each category
    """
    return {
        "papers": search_papers(query, search_type, limit_per_category),
        "sections": search_sections(query, search_type, paper_ids, limit_per_category),
        "notes": search_notes(query, search_type, paper_ids, limit_per_category),
        "summaries": search_summaries(query, search_type, paper_ids, limit_per_category),
    }
