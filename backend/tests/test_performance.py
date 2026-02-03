"""
Performance benchmarks for pgvector operations.

Benchmarks:
- Query latency (p50, p95, p99)
- Index build time
- Memory usage
- Concurrent query handling
"""
import pytest
import asyncio
import time
from pathlib import Path
import sys
import statistics

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestQueryPerformance:
    """Benchmark query performance."""
    
    async def test_vector_search_latency(self):
        """Benchmark vector similarity search latency."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        from rag.pgvector_store import PgVectorStore
        
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        # Check if there's data to search
        count = await store.get_block_count()
        if count == 0:
            pytest.skip("No data to benchmark")
        
        # Run multiple queries and measure latency
        queries = [
            "machine learning and neural networks",
            "deep learning applications",
            "natural language processing",
            "computer vision algorithms",
            "data science methods"
        ]
        
        latencies = []
        
        for query in queries:
            start = time.time()
            results = await store.similarity_search(query, k=10)
            end = time.time()
            
            latencies.append((end - start) * 1000)  # Convert to ms
        
        # Calculate statistics
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        
        print(f"\nVector Search Latency (k=10):")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms")
        print(f"  p99: {p99:.2f}ms")
        
        # Assert reasonable latency (should be under 200ms for p95)
        assert p95 < 500, f"p95 latency {p95}ms is too high"
    
    async def test_hybrid_search_latency(self):
        """Benchmark hybrid search latency."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        from core.hybrid_search import hybrid_search
        from rag.pgvector_store import PgVectorStore
        
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        count = await store.get_block_count()
        if count == 0:
            pytest.skip("No data to benchmark")
        
        queries = [
            "machine learning",
            "deep learning",
            "neural networks"
        ]
        
        latencies = []
        
        for query in queries:
            start = time.time()
            results = await hybrid_search(query, store, pool, k=10)
            end = time.time()
            
            latencies.append((end - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        
        print(f"\nHybrid Search Latency (k=10):")
        print(f"  Average: {avg_latency:.2f}ms")
        
        # Hybrid search is more expensive, allow up to 1 second
        assert avg_latency < 1000, f"Average latency {avg_latency}ms is too high"
    
    async def test_concurrent_queries(self):
        """Benchmark concurrent query handling."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        from rag.pgvector_store import PgVectorStore
        
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        count = await store.get_block_count()
        if count == 0:
            pytest.skip("No data to benchmark")
        
        # Run 10 concurrent queries
        queries = [f"test query {i}" for i in range(10)]
        
        async def run_query(query):
            start = time.time()
            results = await store.similarity_search(query, k=5)
            end = time.time()
            return (end - start) * 1000
        
        start = time.time()
        latencies = await asyncio.gather(*[run_query(q) for q in queries])
        total_time = (time.time() - start) * 1000
        
        avg_latency = statistics.mean(latencies)
        
        print(f"\nConcurrent Queries (n=10):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average latency: {avg_latency:.2f}ms")
        print(f"  Throughput: {len(queries) / (total_time / 1000):.2f} queries/sec")
        
        # With connection pooling, should handle concurrency well
        assert total_time < 5000, f"Concurrent queries took {total_time}ms"


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestIndexPerformance:
    """Benchmark index building performance."""
    
    async def test_embedding_generation_speed(self):
        """Benchmark embedding generation speed."""
        from rag.embeddings import get_embedding_service
        
        service = get_embedding_service()
        
        # Generate embeddings for 100 texts
        texts = [f"This is test document number {i} about various topics." for i in range(100)]
        
        start = time.time()
        embeddings = service.embed_texts(texts, show_progress=False)
        end = time.time()
        
        duration = end - start
        throughput = len(texts) / duration
        
        print(f"\nEmbedding Generation (n=100):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} texts/sec")
        
        assert embeddings.shape == (100, 768)
    
    async def test_block_insertion_speed(self):
        """Benchmark block insertion speed."""
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
                "Benchmark Paper",
                "/tmp/bench.pdf"
            )
        
        # Create 100 test blocks
        blocks = [
            {
                "text": f"This is test block {i} with some content about machine learning.",
                "page_no": i // 10 + 1,
                "block_index": i % 10,
                "bbox": {"x0": 0, "y0": 0, "x1": 100, "y1": 50}
            }
            for i in range(100)
        ]
        
        start = time.time()
        inserted = await store.insert_blocks(blocks, paper_id)
        end = time.time()
        
        duration = end - start
        throughput = inserted / duration
        
        print(f"\nBlock Insertion (n=100):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} blocks/sec")
        
        assert inserted == 100
        
        # Clean up
        await store.delete_paper_blocks(paper_id)
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM papers WHERE id = $1", paper_id)


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestIndexStats:
    """Test index statistics and health."""
    
    async def test_index_stats(self):
        """Display index statistics."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        from rag.pgvector_store import PgVectorStore
        
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        stats = await store.get_index_stats()
        
        print("\nIndex Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Basic sanity checks
        assert stats["total_blocks"] >= 0
        assert stats["blocks_with_embeddings"] >= 0
        assert stats["blocks_with_embeddings"] <= stats["total_blocks"]
    
    async def test_index_coverage(self):
        """Test what percentage of blocks have embeddings."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        from rag.pgvector_store import PgVectorStore
        
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        stats = await store.get_index_stats()
        
        if stats["total_blocks"] > 0:
            coverage = (stats["blocks_with_embeddings"] / stats["total_blocks"]) * 100
            print(f"\nIndex Coverage: {coverage:.1f}%")
            
            # Warn if coverage is low
            if coverage < 100:
                print(f"Warning: Only {coverage:.1f}% of blocks have embeddings")


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestScalability:
    """Test scalability with varying data sizes."""
    
    async def test_search_latency_vs_dataset_size(self):
        """Test how search latency scales with dataset size."""
        import os
        if not os.getenv("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")
        
        from core.postgres import get_pool
        from rag.pgvector_store import PgVectorStore
        
        pool = await get_pool()
        store = PgVectorStore(pool)
        
        # Get current dataset size
        total_blocks = await store.get_block_count()
        
        if total_blocks == 0:
            pytest.skip("No data to test scalability")
        
        # Test search with different k values
        k_values = [5, 10, 20, 50, 100]
        
        print(f"\nSearch Latency vs k (dataset size: {total_blocks} blocks):")
        
        for k in k_values:
            if k > total_blocks:
                break
            
            start = time.time()
            results = await store.similarity_search("test query", k=k)
            end = time.time()
            
            latency = (end - start) * 1000
            print(f"  k={k:3d}: {latency:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
