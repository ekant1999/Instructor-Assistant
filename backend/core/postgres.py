"""
PostgreSQL database connection and configuration for pgvector migration.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import asyncpg
from contextlib import asynccontextmanager

# Environment configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://instructor:password@localhost:5432/instructor_assistant")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    """Initialize PostgreSQL connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=DB_POOL_SIZE,
            command_timeout=60,
        )
    return _pool


async def close_pool():
    """Close the PostgreSQL connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_pool() -> asyncpg.Pool:
    """Get the connection pool, initializing if necessary."""
    if _pool is None:
        return await init_pool()
    return _pool


@asynccontextmanager
async def get_connection():
    """Context manager for getting a connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def init_db() -> None:
    """
    Initialize PostgreSQL database with pgvector extension and schema.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Enable extensions
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        
        # Create papers table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id SERIAL PRIMARY KEY,
                title TEXT,
                source_url TEXT,
                pdf_path TEXT NOT NULL,
                rag_status TEXT,
                rag_error TEXT,
                rag_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create text_blocks table (replaces sections)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS text_blocks (
                id SERIAL PRIMARY KEY,
                paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
                page_no INTEGER NOT NULL,
                block_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding vector(768),
                bbox JSONB,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(paper_id, page_no, block_index)
            );
        """)
        
        # Create HNSW index for vector similarity search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS text_blocks_embedding_idx ON text_blocks 
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)
        
        # Create full-text search index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS text_blocks_fts_idx ON text_blocks 
            USING GIN (to_tsvector('english', text));
        """)
        
        # Create additional indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS text_blocks_paper_id_idx ON text_blocks(paper_id);
        """)
        
        # Create notes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                paper_id INTEGER NULL REFERENCES papers(id) ON DELETE SET NULL,
                body TEXT NOT NULL,
                title TEXT,
                tags_json TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create summaries table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id SERIAL PRIMARY KEY,
                paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
                title TEXT,
                content TEXT NOT NULL,
                agent TEXT,
                style TEXT,
                word_count INTEGER,
                is_edited INTEGER DEFAULT 0,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create question_sets table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS question_sets (
                id SERIAL PRIMARY KEY,
                prompt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create questions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                set_id INTEGER NOT NULL REFERENCES question_sets(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                text TEXT NOT NULL,
                options_json TEXT,
                answer TEXT,
                explanation TEXT,
                reference TEXT
            );
        """)
        
        # Create rag_qna table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_qna (
                id SERIAL PRIMARY KEY,
                paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources_json TEXT,
                scope TEXT,
                provider TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)


async def health_check() -> bool:
    """Check if PostgreSQL connection is healthy."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
