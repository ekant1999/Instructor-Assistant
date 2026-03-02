# pgvector Migration Guide

This guide walks you through migrating from SQLite + FAISS to PostgreSQL + pgvector.

## Overview

The migration provides:
- **Block-level location tracking**: Precise citations with page + block index
- **Better embeddings**: all-mpnet-base-v2 (768D) vs all-MiniLM-L6-v2 (384D)
- **Hybrid search**: Combines vector similarity + full-text search
- **Scalability**: PostgreSQL handles larger datasets better than SQLite
- **HNSW indexing**: Fast incremental updates without full reindexing

## Prerequisites

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Docker (recommended for development):**
```bash
docker run --name instructor-postgres \
  -e POSTGRES_USER=instructor \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=instructor_assistant \
  -p 5432:5432 \
  -d pgvector/pgvector:pg15
```

### 2. Install pgvector Extension

If using native PostgreSQL (not Docker):

```bash
# macOS
brew install pgvector

# Ubuntu/Debian
sudo apt install postgresql-15-pgvector
```

If using Docker, pgvector is already included in the `pgvector/pgvector` image.

### 3. Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres

# Create user and database
CREATE USER instructor WITH PASSWORD 'password';
CREATE DATABASE instructor_assistant OWNER instructor;

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE instructor_assistant TO instructor;

# Exit psql
\q
```

### 4. Update Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `asyncpg==0.29.0` - async PostgreSQL driver
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `pgvector==0.2.5` - pgvector client library
- Upgraded `sentence-transformers>=2.3.0`

## Migration Steps

### Step 1: Configure Environment

Update your `.env` file with PostgreSQL connection:

```bash
# Copy example and edit
cp .env.example .env

# Edit these values:
DATABASE_URL=postgresql://instructor:password@localhost:5432/instructor_assistant
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
EMBEDDING_DIMENSION=768
EMBEDDING_DEVICE=cpu  # or 'cuda' if you have GPU
```

### Step 2: Initialize PostgreSQL Schema

Run the initialization script:

```bash
cd backend
python -c "import asyncio; from core.postgres import init_db; asyncio.run(init_db())"
```

This will:
- Enable pgvector and pg_trgm extensions
- Create tables (papers, text_blocks, notes, summaries, etc.)
- Create HNSW indexes for vector search
- Create full-text search indexes

### Step 3: Backup SQLite Database

**Important**: Always backup before migration!

```bash
cp backend/data/app.db backend/data/app.db.backup
```

### Step 4: Run Migration Script

```bash
cd backend
python migrations/migrate_sqlite_to_postgres.py
```

The migration will:
1. Read data from SQLite (`backend/data/app.db`)
2. Transform and insert into PostgreSQL
3. Migrate papers, sections → text_blocks, notes, summaries, questions
4. Validate data integrity by comparing counts
5. Report success or warnings

**Note**: Embeddings are NOT migrated. You'll need to re-index in Step 6.

### Step 5: Verify Migration

Check that data was migrated correctly:

```bash
# Connect to PostgreSQL
psql -U instructor -d instructor_assistant

# Check counts
SELECT 'papers' as table_name, COUNT(*) FROM papers
UNION ALL
SELECT 'text_blocks', COUNT(*) FROM text_blocks
UNION ALL
SELECT 'notes', COUNT(*) FROM notes
UNION ALL
SELECT 'summaries', COUNT(*) FROM summaries;

# Exit
\q
```

### Step 6: Re-index Papers with New Embeddings

Since the embedding model changed (384D → 768D), you need to re-generate embeddings:

```bash
cd backend
python rag/ingest_pgvector.py
```

This will:
1. Extract text blocks with PyMuPDF (page + block index)
2. Apply smart chunking strategy
3. Generate 768D embeddings with all-mpnet-base-v2
4. Insert into PostgreSQL with HNSW indexing

**Time estimate**: ~2-5 minutes per 100-page paper with CPU.

**Progress**: The script shows progress for each paper:
```
Ingesting paper 1: Example Paper Title
  Extracting text blocks...
  Extracted 523 text blocks
  Chunking blocks...
  Created 187 chunks
  Generating embeddings and inserting...
  ✓ Inserted 187 blocks with embeddings
```

### Step 7: Test the System

Test that everything works:

```python
# Test query
import asyncio
from backend.rag.query_pgvector import query_rag

async def test():
    result = await query_rag(
        question="What is the main contribution of this paper?",
        k=6,
        search_type="hybrid"
    )
    print(f"Answer: {result['answer']}")
    print(f"Sources: {result['num_sources']}")

asyncio.run(test())
```

### Step 8: Update Application Code

If you have custom code using the old FAISS-based system, update imports:

**Before:**
```python
from backend.rag.ingest import ingest_single_paper
from backend.rag.query import query_rag
from backend.rag.graph import load_vectorstore
```

**After:**
```python
from backend.rag.ingest_pgvector import ingest_single_paper
from backend.rag.query_pgvector import query_rag
# load_vectorstore is no longer needed - pgvector handles storage
```

## Performance Tuning

### HNSW Index Parameters

Tune these in `.env` based on your needs:

```bash
# Smaller datasets (<10k chunks): faster build, lower recall
HNSW_M=8
HNSW_EF_CONSTRUCTION=32
HNSW_EF_SEARCH=20

# Medium datasets (10k-100k): balanced
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF_SEARCH=40

# Large datasets (>100k): best quality
HNSW_M=32
HNSW_EF_CONSTRUCTION=128
HNSW_EF_SEARCH=80
```

### Connection Pooling

Adjust pool size based on concurrent load:

```bash
# Low concurrency (<5 users)
DB_POOL_SIZE=10

# Medium concurrency (5-20 users)
DB_POOL_SIZE=20

# High concurrency (>20 users)
DB_POOL_SIZE=50
```

### Hybrid Search Weight

Tune alpha based on your use case:

```bash
# Prefer keyword matching (citations, exact terms)
HYBRID_SEARCH_ALPHA=0.3

# Balanced (default)
HYBRID_SEARCH_ALPHA=0.5

# Prefer semantic similarity (concepts, paraphrasing)
HYBRID_SEARCH_ALPHA=0.7
```

## Rollback Strategy

If you need to rollback to SQLite + FAISS:

### 1. Restore SQLite Database

```bash
cp backend/data/app.db.backup backend/data/app.db
```

### 2. Restore Old FAISS Index

If you backed up the `backend/index/` directory:

```bash
# Restore FAISS index
cp -r backend/index.backup backend/index
```

If you didn't backup, re-run the old ingestion:

```bash
cd backend
python rag/ingest.py
```

### 3. Revert Code Changes

```bash
git checkout HEAD -- backend/rag/ingest.py backend/rag/query.py backend/rag/graph.py
```

## Troubleshooting

### "Extension vector does not exist"

**Solution**: Install pgvector extension:

```bash
# macOS
brew install pgvector

# Ubuntu
sudo apt install postgresql-15-pgvector

# Or use Docker image
docker pull pgvector/pgvector:pg15
```

### "Connection refused" or "could not connect to server"

**Solution**: Check PostgreSQL is running:

```bash
# macOS
brew services list | grep postgresql

# Ubuntu
sudo systemctl status postgresql

# Docker
docker ps | grep postgres
```

### "Out of memory" during reindexing

**Solution**: Reduce batch size or use GPU:

```bash
# Use GPU if available
EMBEDDING_DEVICE=cuda

# Or process papers one at a time
python -c "
import asyncio
from backend.rag.ingest_pgvector import ingest_papers_from_db
asyncio.run(ingest_papers_from_db(paper_ids=[1]))  # Process paper 1
asyncio.run(ingest_papers_from_db(paper_ids=[2]))  # Process paper 2
# ...
"
```

### Slow queries

**Solution**: 
1. Check index is created: `\d text_blocks` in psql should show HNSW index
2. Increase `HNSW_EF_SEARCH` for better recall at cost of speed
3. Run `VACUUM ANALYZE text_blocks;` to update statistics

### Migration validation warnings

If counts don't match, check:

```sql
-- Find papers missing from migration
SELECT id, title FROM papers 
WHERE id NOT IN (SELECT DISTINCT paper_id FROM text_blocks);

-- Check for NULL embeddings
SELECT COUNT(*) FROM text_blocks WHERE embedding IS NULL;
```

## Success Metrics

After migration, verify:

1. **Data Integrity**: All papers, notes, summaries migrated ✓
2. **Embeddings Generated**: `text_blocks` has 768D embeddings ✓
3. **Search Quality**: Queries return relevant results ✓
4. **Performance**: Query latency <200ms for k=10 ✓
5. **Block Location**: Citations show "Page X, Block Y" ✓

Check metrics:

```python
import asyncio
from backend.core.postgres import get_pool
from backend.rag.pgvector_store import PgVectorStore

async def check_metrics():
    pool = await get_pool()
    store = PgVectorStore(pool)
    stats = await store.get_index_stats()
    print("Index Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

asyncio.run(check_metrics())
```

## Next Steps

After successful migration:

1. **Test thoroughly**: Run queries on all paper types
2. **Monitor performance**: Use slow query logs to identify bottlenecks
3. **Enable reranking**: Consider adding cross-encoder reranking
4. **Implement highlighting**: Use bbox coordinates for PDF highlighting
5. **Scale if needed**: Add read replicas or use Citus for horizontal scaling

## Getting Help

If you encounter issues:

1. Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-15-main.log`
2. Check application logs for detailed error messages
3. Verify environment variables are set correctly
4. Test database connection: `psql -U instructor -d instructor_assistant`

For more help, refer to:
- [pgvector documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [sentence-transformers documentation](https://www.sbert.net/)
