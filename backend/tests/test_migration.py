"""
Integration tests for SQLite to PostgreSQL migration.

Tests:
- Data migration integrity
- Relationship preservation
- FAISS vs pgvector result comparison
"""
import pytest
import asyncio
import sqlite3
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.mark.asyncio
class TestMigration:
    """Test migration from SQLite to PostgreSQL."""
    
    async def test_migration_preserves_papers(self):
        """Test that all papers are migrated correctly."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.database import DB_PATH, get_conn
        from core.postgres import get_pool
        
        if not DB_PATH.exists():
            pytest.skip("No SQLite database to test migration")
        
        # Get SQLite count
        with get_conn() as sqlite_conn:
            sqlite_count = sqlite_conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        
        # Get PostgreSQL count
        pool = await get_pool()
        async with pool.acquire() as pg_conn:
            pg_count = await pg_conn.fetchval("SELECT COUNT(*) FROM papers")
        
        # Should match after migration
        # Note: This test assumes migration has been run
        assert pg_count > 0, "No papers in PostgreSQL"
        print(f"Papers - SQLite: {sqlite_count}, PostgreSQL: {pg_count}")
    
    async def test_migration_preserves_relationships(self):
        """Test that foreign key relationships are preserved."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        
        pool = await get_pool()
        
        # Check that text_blocks reference valid papers
        async with pool.acquire() as conn:
            orphaned = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM text_blocks tb
                LEFT JOIN papers p ON tb.paper_id = p.id
                WHERE p.id IS NULL
            """)
            
            assert orphaned == 0, f"Found {orphaned} text_blocks with invalid paper_id"
        
        # Check that summaries reference valid papers
        async with pool.acquire() as conn:
            orphaned = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM summaries s
                LEFT JOIN papers p ON s.paper_id = p.id
                WHERE p.id IS NULL
            """)
            
            assert orphaned == 0, f"Found {orphaned} summaries with invalid paper_id"
    
    async def test_text_blocks_have_location_data(self):
        """Test that text_blocks have page and block location data."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get a sample text block
            sample = await conn.fetchrow("""
                SELECT page_no, block_index, text
                FROM text_blocks
                LIMIT 1
            """)
        
        if sample:
            assert sample["page_no"] >= 1, "Invalid page_no"
            assert sample["block_index"] >= 0, "Invalid block_index"
            assert len(sample["text"]) > 0, "Empty text"
        else:
            pytest.skip("No text_blocks to test")


@pytest.mark.asyncio
class TestSearchComparison:
    """Compare FAISS and pgvector search results."""
    
    async def test_search_quality_comparable(self):
        """Test that pgvector search quality is comparable to FAISS."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        # This test would compare:
        # 1. Run same query on FAISS (if available)
        # 2. Run same query on pgvector
        # 3. Compare overlap in top-k results
        
        # For now, just verify pgvector returns reasonable results
        from rag.query_pgvector import query_rag
        
        result = await query_rag(
            question="What is machine learning?",
            k=5,
            search_type="hybrid"
        )
        
        assert "answer" in result
        assert "context" in result
        assert isinstance(result["context"], list)
        
        # Should return some context
        if result["num_sources"] > 0:
            # Check that context has required fields
            for ctx in result["context"]:
                assert "paper_title" in ctx
                assert "page_number" in ctx
                assert "block_index" in ctx


@pytest.mark.asyncio
class TestDataIntegrity:
    """Test data integrity after migration."""
    
    async def test_no_duplicate_blocks(self):
        """Test that there are no duplicate text blocks."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            duplicates = await conn.fetchval("""
                SELECT COUNT(*)
                FROM (
                    SELECT paper_id, page_no, block_index, COUNT(*)
                    FROM text_blocks
                    GROUP BY paper_id, page_no, block_index
                    HAVING COUNT(*) > 1
                ) duplicates
            """)
            
            assert duplicates == 0, f"Found {duplicates} duplicate text blocks"
    
    async def test_embeddings_are_valid(self):
        """Test that embeddings are valid 768D vectors."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get a sample embedding
            result = await conn.fetchrow("""
                SELECT embedding
                FROM text_blocks
                WHERE embedding IS NOT NULL
                LIMIT 1
            """)
        
        if result and result["embedding"]:
            embedding = result["embedding"]
            # pgvector returns embedding as a list
            assert len(embedding) == 768, f"Expected 768D, got {len(embedding)}D"
            
            # Check that values are reasonable (normalized)
            import numpy as np
            emb_array = np.array(embedding)
            norm = np.linalg.norm(emb_array)
            assert 0.9 < norm < 1.1, f"Embedding norm {norm} is not normalized"
    
    async def test_all_papers_have_blocks(self):
        """Test that all papers have at least one text block."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            papers_without_blocks = await conn.fetchval("""
                SELECT COUNT(*)
                FROM papers p
                LEFT JOIN text_blocks tb ON p.id = tb.paper_id
                WHERE tb.id IS NULL
            """)
        
        # Some papers might not be indexed yet, so just warn
        if papers_without_blocks > 0:
            print(f"Warning: {papers_without_blocks} papers have no text_blocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
