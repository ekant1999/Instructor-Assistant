-- PostgreSQL initialization script for pgvector
-- Enable required extensions

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for text search

-- Papers table
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

-- Text blocks table (replaces sections with block-level tracking)
CREATE TABLE IF NOT EXISTS text_blocks (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    page_no INTEGER NOT NULL,
    block_index INTEGER NOT NULL,  -- Block position on page
    text TEXT NOT NULL,
    embedding vector(768),  -- 768D for all-mpnet-base-v2
    bbox JSONB,  -- {x0, y0, x1, y1} for future highlighting
    metadata JSONB,  -- Additional metadata
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(paper_id, page_no, block_index)
);

-- Create HNSW index for vector similarity search
-- HNSW is optimal for incremental updates and full CRUD support
CREATE INDEX IF NOT EXISTS text_blocks_embedding_idx ON text_blocks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX IF NOT EXISTS text_blocks_fts_idx ON text_blocks 
USING GIN (to_tsvector('english', text));

-- Additional indexes for query performance
CREATE INDEX IF NOT EXISTS text_blocks_paper_id_idx ON text_blocks(paper_id);
CREATE INDEX IF NOT EXISTS text_blocks_page_no_idx ON text_blocks(paper_id, page_no);

-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NULL REFERENCES papers(id) ON DELETE SET NULL,
    body TEXT NOT NULL,
    title TEXT,
    tags_json TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Summaries table
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

-- Question sets table
CREATE TABLE IF NOT EXISTS question_sets (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Questions table
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

-- RAG Q&A history table
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

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS notes_paper_id_idx ON notes(paper_id);
CREATE INDEX IF NOT EXISTS summaries_paper_id_idx ON summaries(paper_id);
CREATE INDEX IF NOT EXISTS questions_set_id_idx ON questions(set_id);
CREATE INDEX IF NOT EXISTS rag_qna_paper_id_idx ON rag_qna(paper_id);
