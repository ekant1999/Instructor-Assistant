"""
Unit tests for pgvector operations.

Tests:
- Embedding generation
- Vector insertion and retrieval
- Hybrid search accuracy
- Block-level location tracking
"""
import pytest
import asyncio
import numpy as np
from pathlib import Path
import sys

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from rag.embeddings import EmbeddingService, get_embedding_service
from rag.chunking import chunk_text_blocks, simple_chunk_blocks
from core.pdf import extract_text_blocks


class TestEmbeddingService:
    """Test embedding generation."""
    
    def test_init_default_model(self):
        """Test initialization with default model."""
        service = EmbeddingService()
        assert service.dimension == 768  # all-mpnet-base-v2
        assert "mpnet" in service.model_name.lower()
    
    def test_embed_single_text(self):
        """Test embedding a single text."""
        service = get_embedding_service()
        text = "This is a test document about machine learning."
        embedding = service.embed_query(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)
        assert np.abs(np.linalg.norm(embedding) - 1.0) < 0.01  # Should be normalized
    
    def test_embed_multiple_texts(self):
        """Test embedding multiple texts."""
        service = get_embedding_service()
        texts = [
            "Machine learning is a subset of AI.",
            "Deep learning uses neural networks.",
            "Natural language processing handles text."
        ]
        embeddings = service.embed_texts(texts, show_progress=False)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 768)
        
        # Check normalization
        for emb in embeddings:
            assert np.abs(np.linalg.norm(emb) - 1.0) < 0.01
    
    def test_similarity_computation(self):
        """Test that similar texts have higher similarity."""
        service = get_embedding_service()
        
        text1 = "Machine learning and artificial intelligence"
        text2 = "AI and ML are related fields"
        text3 = "I like to eat pizza for dinner"
        
        emb1 = service.embed_query(text1)
        emb2 = service.embed_query(text2)
        emb3 = service.embed_query(text3)
        
        # Cosine similarity (dot product since normalized)
        sim_12 = np.dot(emb1, emb2)
        sim_13 = np.dot(emb1, emb3)
        
        # Similar texts should have higher similarity
        assert sim_12 > sim_13
        assert sim_12 > 0.5  # Related topics
        assert sim_13 < 0.5  # Unrelated topics


class TestChunking:
    """Test chunking strategies."""
    
    def test_simple_chunking(self):
        """Test simple block combining."""
        blocks = [
            {"text": "A" * 100, "page_no": 1, "block_index": 0, "bbox": {}},
            {"text": "B" * 100, "page_no": 1, "block_index": 1, "bbox": {}},
            {"text": "C" * 100, "page_no": 1, "block_index": 2, "bbox": {}},
        ]
        
        chunks = simple_chunk_blocks(blocks, max_chars=250)
        
        # Should combine first two blocks, third separate
        assert len(chunks) == 2
        assert "A" in chunks[0]["text"] and "B" in chunks[0]["text"]
        assert "C" in chunks[1]["text"]
    
    def test_smart_chunking_respects_target_size(self):
        """Test that smart chunking creates appropriately sized chunks."""
        blocks = [
            {"text": "A" * 500, "page_no": 1, "block_index": i, "bbox": {}}
            for i in range(10)
        ]
        
        chunks = chunk_text_blocks(blocks, target_size=1000, overlap=200)
        
        # Check chunk sizes
        for chunk in chunks:
            text_len = len(chunk["text"])
            assert text_len >= 100  # min_chunk_size
            # Most chunks should be near target size (with some tolerance)
            assert text_len <= 1500  # Allow some overage
    
    def test_chunking_preserves_metadata(self):
        """Test that chunking preserves block metadata."""
        blocks = [
            {
                "text": "Test block text",
                "page_no": 1,
                "block_index": 0,
                "bbox": {"x0": 0, "y0": 0, "x1": 100, "y1": 50}
            }
        ]
        
        chunks = simple_chunk_blocks(blocks, max_chars=100)
        
        assert len(chunks) == 1
        assert chunks[0]["page_no"] == 1
        assert chunks[0]["block_index"] == 0
        assert chunks[0]["bbox"]["x0"] == 0


@pytest.mark.asyncio
class TestPgVectorStore:
    """Test pgvector store operations."""
    
    async def test_insert_and_search(self):
        """Test inserting blocks and searching."""
        # This test requires a running PostgreSQL instance
        # Skip if DATABASE_URL not configured
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool, init_db
        from rag.pgvector_store import PgVectorStore
        
        # Initialize database
        await init_db()
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        # Create test paper
        async with pool.acquire() as conn:
            paper_id = await conn.fetchval(
                "INSERT INTO papers (title, pdf_path) VALUES ($1, $2) RETURNING id",
                "Test Paper",
                "/tmp/test.pdf"
            )
        
        # Create test blocks
        blocks = [
            {
                "text": "This is about machine learning and neural networks.",
                "page_no": 1,
                "block_index": 0,
                "bbox": {"x0": 0, "y0": 0, "x1": 100, "y1": 50}
            },
            {
                "text": "Deep learning is a subset of machine learning.",
                "page_no": 1,
                "block_index": 1,
                "bbox": {"x0": 0, "y0": 60, "x1": 100, "y1": 110}
            },
            {
                "text": "Pizza is a delicious Italian food.",
                "page_no": 2,
                "block_index": 0,
                "bbox": {"x0": 0, "y0": 0, "x1": 100, "y1": 50}
            }
        ]
        
        # Insert blocks
        inserted = await store.insert_blocks(blocks, paper_id)
        assert inserted == 3
        
        # Search for ML-related content
        results = await store.similarity_search("neural networks", k=2)
        
        assert len(results) == 2
        assert "neural networks" in results[0]["text"] or "machine learning" in results[0]["text"]
        assert results[0]["page_no"] in [1, 2]
        assert results[0]["block_index"] >= 0
        
        # Check similarity scores
        assert results[0]["similarity"] > 0.5
        assert results[0]["similarity"] > results[1]["similarity"]
        
        # Clean up
        await store.delete_paper_blocks(paper_id)
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM papers WHERE id = $1", paper_id)
    
    async def test_block_location_tracking(self):
        """Test that block locations are correctly tracked."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool, init_db
        from rag.pgvector_store import PgVectorStore
        
        await init_db()
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        # Create test paper
        async with pool.acquire() as conn:
            paper_id = await conn.fetchval(
                "INSERT INTO papers (title, pdf_path) VALUES ($1, $2) RETURNING id",
                "Location Test Paper",
                "/tmp/test.pdf"
            )
        
        # Create blocks with specific locations
        blocks = [
            {
                "text": "Block on page 5, position 3",
                "page_no": 5,
                "block_index": 3,
                "bbox": {"x0": 50, "y0": 200, "x1": 150, "y1": 250}
            }
        ]
        
        await store.insert_blocks(blocks, paper_id)
        
        # Search and verify location
        results = await store.similarity_search("Block on page 5", k=1)
        
        assert len(results) == 1
        assert results[0]["page_no"] == 5
        assert results[0]["block_index"] == 3
        assert results[0]["bbox"]["x0"] == 50
        
        # Clean up
        await store.delete_paper_blocks(paper_id)
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM papers WHERE id = $1", paper_id)


@pytest.mark.asyncio
class TestHybridSearch:
    """Test hybrid search combining vector + FTS."""
    
    async def test_hybrid_search_fusion(self):
        """Test that hybrid search combines vector and FTS results."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool, init_db
        from core.hybrid_search import hybrid_search
        from rag.pgvector_store import PgVectorStore
        
        await init_db()
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        # Create test paper
        async with pool.acquire() as conn:
            paper_id = await conn.fetchval(
                "INSERT INTO papers (title, pdf_path) VALUES ($1, $2) RETURNING id",
                "Hybrid Test Paper",
                "/tmp/test.pdf"
            )
        
        # Create blocks with specific keywords
        blocks = [
            {
                "text": "The quick brown fox jumps over the lazy dog.",
                "page_no": 1,
                "block_index": 0,
                "bbox": {}
            },
            {
                "text": "Machine learning models can predict outcomes.",
                "page_no": 1,
                "block_index": 1,
                "bbox": {}
            },
            {
                "text": "Neural networks are used in deep learning.",
                "page_no": 1,
                "block_index": 2,
                "bbox": {}
            }
        ]
        
        await store.insert_blocks(blocks, paper_id)
        
        # Test hybrid search with keyword that appears in text
        results = await hybrid_search(
            "neural networks machine learning",
            store,
            pool,
            k=2,
            alpha=0.5  # Balanced
        )
        
        assert len(results) > 0
        # Results should have both source indicators
        assert any("sources" in r for r in results)
        
        # Test alpha weighting
        results_vector = await hybrid_search(
            "neural networks",
            store,
            pool,
            k=2,
            alpha=1.0  # Vector only
        )
        
        results_fts = await hybrid_search(
            "neural networks",
            store,
            pool,
            k=2,
            alpha=0.0  # FTS only
        )
        
        # Both should return results
        assert len(results_vector) > 0
        assert len(results_fts) > 0
        
        # Clean up
        await store.delete_paper_blocks(paper_id)
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM papers WHERE id = $1", paper_id)


class TestPDFParsing:
    """Test PDF text block extraction."""
    
    def test_extract_blocks_with_pymupdf(self):
        """Test block extraction from a real PDF."""
        # This test requires a sample PDF file
        # Skip if test PDF doesn't exist
        test_pdf = Path(__file__).parent / "fixtures" / "sample.pdf"
        if not test_pdf.exists():
            pytest.skip("Sample PDF not found")
        
        blocks = extract_text_blocks(test_pdf)
        
        assert len(blocks) > 0
        
        # Check structure
        for block in blocks:
            assert "page_no" in block
            assert "block_index" in block
            assert "text" in block
            assert "bbox" in block
            
            assert block["page_no"] >= 1
            assert block["block_index"] >= 0
            assert len(block["text"]) > 0
            
            # Check bbox has required fields
            bbox = block["bbox"]
            assert "x0" in bbox and "y0" in bbox
            assert "x1" in bbox and "y1" in bbox


def test_imports():
    """Test that all new modules can be imported."""
    from rag.embeddings import EmbeddingService, get_embedding_service
    from rag.chunking import chunk_text_blocks, simple_chunk_blocks
    from rag.pgvector_store import PgVectorStore
    from core.postgres import init_db, get_pool
    from core.hybrid_search import hybrid_search, reciprocal_rank_fusion
    
    # If we get here, all imports succeeded
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
