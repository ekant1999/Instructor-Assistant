"""
pgvector store for vector similarity search with PostgreSQL.

Uses HNSW indexing for efficient similarity search with incremental updates.
"""
import json
from typing import List, Dict, Any, Optional, Set
import asyncpg
import numpy as np

from .embeddings import get_embedding_service


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(val) for key, val in value.items()}
    return value


class PgVectorStore:
    """Vector store using PostgreSQL with pgvector extension."""
    
    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize pgvector store.
        
        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool
        self.embedder = get_embedding_service()
    
    async def insert_blocks(
        self,
        blocks: List[Dict[str, Any]],
        paper_id: int
    ) -> int:
        """
        Insert text blocks with embeddings.
        
        Args:
            blocks: List of block dictionaries with text, page_no, block_index, bbox
            paper_id: ID of the paper these blocks belong to
        
        Returns:
            Number of blocks inserted
        """
        if not blocks:
            return 0
        
        # Extract texts for embedding (sanitize NULL bytes)
        texts = []
        for b in blocks:
            raw_text = b.get("text") or ""
            clean_text = raw_text.replace("\x00", "")
            if clean_text != raw_text:
                b["text"] = clean_text
            # Sanitize nested metadata/bbox to avoid invalid UTF-8 escapes
            if "metadata" in b:
                b["metadata"] = _sanitize_value(b.get("metadata"))
            if "bbox" in b:
                b["bbox"] = _sanitize_value(b.get("bbox"))
            texts.append(clean_text)
        
        # Generate embeddings
        embeddings = self.embedder.embed_texts(texts, show_progress=True)
        
        # Prepare data for insertion
        insert_data = []
        for i, block in enumerate(blocks):
            insert_data.append((
                paper_id,
                block["page_no"],
                block["block_index"],
                block["text"],
                embeddings[i].tolist(),  # Convert numpy array to list
                json.dumps(block.get("bbox")) if block.get("bbox") else None,
                json.dumps(block.get("metadata")) if block.get("metadata") else None
            ))
        
        # Insert in batches
        async with self.pool.acquire() as conn:
            # Use ON CONFLICT to handle duplicates
            await conn.executemany(
                """
                INSERT INTO text_blocks 
                (paper_id, page_no, block_index, text, embedding, bbox, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (paper_id, page_no, block_index) 
                DO UPDATE SET 
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    bbox = EXCLUDED.bbox,
                    metadata = EXCLUDED.metadata
                """,
                insert_data
            )
        
        return len(insert_data)
    
    async def delete_paper_blocks(self, paper_id: int) -> int:
        """
        Delete all blocks for a paper.
        
        Args:
            paper_id: ID of the paper
        
        Returns:
            Number of blocks deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM text_blocks WHERE paper_id = $1",
                paper_id
            )
            # Extract count from result string "DELETE N"
            count = int(result.split()[-1]) if result else 0
            return count
    
    async def similarity_search(
        self,
        query: str,
        k: int = 10,
        paper_ids: Optional[List[int]] = None,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search using pgvector HNSW index.
        
        Args:
            query: Query text
            k: Number of results to return
            paper_ids: Optional list of paper IDs to filter by
            threshold: Minimum similarity threshold (0-1)
        
        Returns:
            List of results with text, metadata, and similarity scores
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
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
                1 - (tb.embedding <=> $1::vector) as similarity
            FROM text_blocks tb
            JOIN papers p ON tb.paper_id = p.id
            WHERE tb.embedding IS NOT NULL
        """
        
        params = [query_embedding.tolist()]
        param_idx = 2
        
        # Add paper_ids filter if provided
        if paper_ids:
            sql += f" AND tb.paper_id = ANY(${param_idx})"
            params.append(paper_ids)
            param_idx += 1
        
        # Add similarity threshold if provided
        if threshold > 0:
            sql += f" AND (1 - (tb.embedding <=> $1::vector)) >= ${param_idx}"
            params.append(threshold)
            param_idx += 1
        
        # Order by similarity and limit
        sql += f" ORDER BY tb.embedding <=> $1::vector LIMIT ${param_idx}"
        params.append(k)
        
        # Execute query
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        
        # Format results
        results = []
        for row in rows:
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
                "similarity": float(row["similarity"])
            })
        
        return results
    
    async def get_block_count(self, paper_id: Optional[int] = None) -> int:
        """
        Get count of text blocks.
        
        Args:
            paper_id: Optional paper ID to filter by
        
        Returns:
            Number of blocks
        """
        async with self.pool.acquire() as conn:
            if paper_id:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM text_blocks WHERE paper_id = $1",
                    paper_id
                )
            else:
                count = await conn.fetchval("SELECT COUNT(*) FROM text_blocks")
        
        return count
    
    async def get_papers_with_embeddings(self) -> List[int]:
        """
        Get list of paper IDs that have embeddings.
        
        Returns:
            List of paper IDs
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT paper_id 
                FROM text_blocks 
                WHERE embedding IS NOT NULL
                ORDER BY paper_id
                """
            )
        
        return [row["paper_id"] for row in rows]
    
    async def update_hnsw_parameters(
        self,
        m: int = 16,
        ef_construction: int = 64
    ):
        """
        Update HNSW index parameters (requires recreating the index).
        
        Args:
            m: Number of connections per layer (higher = better recall, more memory)
            ef_construction: Size of dynamic candidate list (higher = better quality, slower build)
        """
        async with self.pool.acquire() as conn:
            # Drop existing index
            await conn.execute("DROP INDEX IF EXISTS text_blocks_embedding_idx")
            
            # Create new index with updated parameters
            await conn.execute(f"""
                CREATE INDEX text_blocks_embedding_idx ON text_blocks 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = {m}, ef_construction = {ef_construction})
            """)
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the pgvector index.
        
        Returns:
            Dictionary with index statistics
        """
        async with self.pool.acquire() as conn:
            # Get total blocks
            total_blocks = await conn.fetchval("SELECT COUNT(*) FROM text_blocks")
            
            # Get blocks with embeddings
            blocks_with_embeddings = await conn.fetchval(
                "SELECT COUNT(*) FROM text_blocks WHERE embedding IS NOT NULL"
            )
            
            # Get unique papers
            unique_papers = await conn.fetchval(
                "SELECT COUNT(DISTINCT paper_id) FROM text_blocks"
            )
            
            # Get index size (approximate)
            index_info = await conn.fetchrow("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('text_blocks')) as table_size,
                    pg_size_pretty(pg_relation_size('text_blocks_embedding_idx')) as index_size
            """)
        
        return {
            "total_blocks": total_blocks,
            "blocks_with_embeddings": blocks_with_embeddings,
            "unique_papers": unique_papers,
            "table_size": index_info["table_size"] if index_info else "N/A",
            "index_size": index_info["index_size"] if index_info else "N/A"
        }


async def create_pgvector_store(pool: asyncpg.Pool) -> PgVectorStore:
    """
    Factory function to create a pgvector store instance.
    
    Args:
        pool: asyncpg connection pool
    
    Returns:
        Initialized PgVectorStore
    """
    return PgVectorStore(pool)
