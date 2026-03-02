# Hybrid Search Documentation

## Overview

The Instructor Assistant now supports **both keyword-based and embedding-based search** for documents and PDFs across the entire application. You can choose between three search modes:

1. **Keyword Search** - Fast, exact text matching using SQLite FTS5 (Full-Text Search)
2. **Embedding Search** - Semantic similarity using FAISS with HuggingFace embeddings
3. **Hybrid Search** - Combines both keyword and embedding search for best results

---

## Search Modes

### 1. Keyword Search (`search_type="keyword"`)

**Technology**: SQLite FTS5 (Full-Text Search 5)

**How it works**:
- Uses inverted index for fast text lookup
- Matches exact words and phrases
- Best for finding specific terms, names, or phrases

**Use cases**:
- Finding papers by title keywords
- Searching for specific terms in PDFs
- Looking up exact phrases or terminology

**Example**:
```python
# Search for papers containing "neural network"
papers = search_papers("neural network", search_type="keyword")

# Search PDF sections for "introduction"
sections = search_sections("introduction", search_type="keyword", paper_ids=[1])
```

### 2. Embedding Search (`search_type="embedding"`)

**Technology**: FAISS + HuggingFace Embeddings (sentence-transformers/all-MiniLM-L6-v2)

**How it works**:
- Converts text to vector embeddings
- Finds semantically similar content
- Best for conceptual queries and understanding meaning

**Use cases**:
- Finding similar concepts without exact word matches
- Understanding related topics
- Semantic question answering

**Requirements**:
- Requires FAISS index to be built (run RAG ingestion)
- Primarily works with PDF sections in the RAG system

**Example**:
```python
# Find sections about machine learning concepts
result = query_rag(
    "How does the model learn patterns?",
    search_type="embedding"
)
```

### 3. Hybrid Search (`search_type="hybrid"`)

**How it works**:
- Combines results from both keyword and embedding search
- Retrieves from both FTS5 and FAISS indexes
- Merges and ranks results

**Use cases**:
- Best overall search experience
- When you want both exact matches AND semantic similarity
- Comprehensive document retrieval

**Example**:
```python
# Get both exact matches and semantically similar content
result = query_rag(
    "neural network architecture",
    search_type="hybrid",
    k=10  # 5 from keyword, 5 from embedding
)
```

---

## API Endpoints

### 1. Search Papers

**GET** `/api/papers?q={query}&search_type={type}`

**Parameters**:
- `q` (optional): Search query string
- `search_type` (optional): `"keyword"`, `"embedding"`, or `"hybrid"` (default: `"keyword"`)

**Example**:
```bash
curl "http://localhost:8010/api/papers?q=neural&search_type=keyword"
```

### 2. Search Sections

**GET** `/api/papers/{paper_id}/sections?q={query}&search_type={type}`

**Parameters**:
- `paper_id`: Paper ID
- `q` (optional): Search query
- `search_type` (optional): Search mode
- `include_text`: Include full text (default: true)
- `max_chars`: Truncate text to N characters

**Example**:
```bash
curl "http://localhost:8010/api/papers/1/sections?q=introduction&search_type=keyword"
```

### 3. Search Notes

**GET** `/api/notes?q={query}&search_type={type}&paper_ids={ids}`

**Parameters**:
- `q` (optional): Search query
- `search_type` (optional): Search mode
- `paper_ids` (optional): Comma-separated paper IDs to filter by

**Example**:
```bash
curl "http://localhost:8010/api/notes?q=findings&search_type=keyword&paper_ids=1,2"
```

### 4. Search Summaries

**GET** `/api/papers/{paper_id}/summaries?q={query}&search_type={type}`

**Parameters**:
- `paper_id`: Paper ID
- `q` (optional): Search query
- `search_type` (optional): Search mode

**Example**:
```bash
curl "http://localhost:8010/api/papers/1/summaries?q=conclusion&search_type=keyword"
```

### 5. Unified Search

**POST** `/api/search`

Search across all categories (papers, sections, notes, summaries) at once.

**Request Body**:
```json
{
  "query": "neural network",
  "search_type": "keyword",
  "paper_ids": [1, 2],
  "limit": 20
}
```

**Response**:
```json
{
  "query": "neural network",
  "search_type": "keyword",
  "results": [
    {
      "id": 1,
      "relevance_score": -1.5e-06,
      "result_type": "paper",
      "data": { ... }
    },
    {
      "id": 5,
      "relevance_score": -2.1e-06,
      "result_type": "section",
      "data": { ... }
    }
  ],
  "total_results": 15
}
```

### 6. RAG Query with Search Type

**POST** `/api/rag/query`

**Request Body**:
```json
{
  "question": "What is the main finding?",
  "search_type": "hybrid",
  "k": 6,
  "paper_ids": [1],
  "provider": "openai"
}
```

**Search Type Options**:
- `"keyword"` - Use FTS5 text search only
- `"embedding"` - Use FAISS vector search only (default)
- `"hybrid"` - Use both keyword and embedding search

---

## Frontend API Usage

### TypeScript Client

```typescript
import { listPapers, listNotes, ragQuery, unifiedSearch } from '@/lib/api';

// Search papers
const papers = await listPapers("machine learning", "keyword");

// Search notes
const notes = await listNotes("findings", "keyword", [1, 2]);

// RAG query with hybrid search
const ragResult = await ragQuery({
  question: "What are the key results?",
  search_type: "hybrid",
  k: 10,
  paper_ids: [1]
});

// Unified search across all categories
const searchResults = await unifiedSearch({
  query: "neural network",
  search_type: "hybrid",
  limit: 20
});
```

---

## Database Schema

### FTS5 Virtual Tables

The following FTS5 virtual tables are automatically created and kept in sync with the main tables:

1. **papers_fts**
   - Indexed fields: `title`, `source_url`
   - Linked to: `papers` table

2. **sections_fts**
   - Indexed fields: `text`
   - Metadata: `paper_id`, `page_no`
   - Linked to: `sections` table

3. **notes_fts**
   - Indexed fields: `title`, `body`, `tags_json`
   - Metadata: `paper_id`
   - Linked to: `notes` table

4. **summaries_fts**
   - Indexed fields: `title`, `content`
   - Metadata: `paper_id`
   - Linked to: `summaries` table

### Automatic Synchronization

Triggers ensure FTS5 tables stay synchronized with main tables:
- Insert triggers: Add to FTS index when new record created
- Update triggers: Update FTS index when record modified
- Delete triggers: Remove from FTS index when record deleted

---

## Implementation Details

### Backend Structure

```
backend/
├── core/
│   ├── database.py          # FTS5 table creation and triggers
│   └── search.py            # Hybrid search service
├── rag/
│   ├── query.py             # RAG query with search_type support
│   └── graph.py             # FAISS vector retrieval
└── main.py                  # API endpoints with search parameters
```

### Key Functions

**backend/core/search.py**:
- `search_papers()` - Search papers by title/URL
- `search_sections()` - Search PDF content
- `search_notes()` - Search notes by title/body/tags
- `search_summaries()` - Search summaries by title/content
- `search_all()` - Unified search across all tables

**backend/rag/query.py**:
- `query_rag()` - Enhanced with `search_type` parameter
- Supports keyword, embedding, and hybrid retrieval

---

## Performance Characteristics

### Keyword Search (FTS5)
- ✅ **Fast**: Milliseconds for most queries
- ✅ **No preprocessing**: Works immediately after data insertion
- ✅ **Low memory**: Uses SQLite's built-in indexing
- ⚠️ **Exact matching**: Only finds exact words/phrases

### Embedding Search (FAISS)
- ✅ **Semantic**: Finds conceptually similar content
- ✅ **Context-aware**: Understands meaning, not just keywords
- ⚠️ **Slower**: Requires vector computation
- ⚠️ **Requires indexing**: Must run RAG ingestion first

### Hybrid Search
- ✅ **Best of both**: Combines speed and semantics
- ✅ **Comprehensive**: Finds both exact matches and related content
- ⚠️ **Requires both**: Needs FTS5 tables AND FAISS index

---

## Automatic Indexing

### FTS5 (Keyword Search) - Automatic via Triggers

- **No action needed**: FTS5 tables update automatically when data changes
- **Instant**: Updates happen synchronously via SQL triggers
- **Always synchronized**: Papers, sections, notes, and summaries are always searchable

### FAISS (Embedding Search) - Automatic Background Indexing

- **Auto-indexes new papers**: When you add a paper, it's automatically indexed in the background
- **Non-blocking**: API returns immediately; indexing happens asynchronously
- **Status tracking**: Check `rag_status` field to monitor indexing progress

#### Paper Status Fields

```json
{
  "id": 1,
  "title": "My Paper",
  "rag_status": "indexed",           // null → 'indexed' → 'error'
  "rag_error": null,                 // Error message if failed
  "rag_updated_at": "2026-01-29 ..."  // Last indexing time
}
```

#### Disable Auto-Indexing (Optional)

```python
# For bulk imports, disable auto-indexing
add_paper(url, auto_index=False)

# Then manually reindex all at once
POST /api/rag/ingest
```

See **AUTO_INDEXING_GUIDE.md** for complete details.

---

## Migration Notes

### Backward Compatibility

All existing endpoints remain backward compatible:
- Calling without search parameters returns all results (no filtering)
- Default search type is `"keyword"` for new endpoints
- RAG system defaults to `"embedding"` (existing behavior)
- Auto-indexing is enabled by default (can be disabled)

### Database Migration

FTS5 tables are created automatically on server startup:
- Runs during `init_db()` in database initialization
- Populates FTS tables from existing data
- Safe to run multiple times (idempotent)

### First-Time Setup

If you have existing papers that aren't indexed for embedding search:

```bash
# Reindex all papers
POST /api/rag/ingest
{
  "paper_ids": null
}
```

After this, all **new** papers will auto-index automatically.

---

## Testing

Run the test suite:

```bash
cd /Users/ekantkapgate/Instructor-Assistant
python backend/test_search.py
```

**Test Coverage**:
- ✓ FTS5 table creation
- ✓ Paper keyword search
- ✓ Section keyword search
- ✓ Note keyword search (if notes exist)
- ✓ Unified search
- ✓ RAG integration with all search types

---

## Examples

### Example 1: Find papers about "machine learning"

```python
from backend.core.search import search_papers

# Keyword search
papers = search_papers("machine learning", search_type="keyword", limit=10)
for paper in papers:
    print(f"{paper['title']} (score: {paper['rank']})")
```

### Example 2: Search PDF content with hybrid approach

```python
from backend.rag.query import query_rag

result = query_rag(
    question="What are the main contributions?",
    search_type="hybrid",  # Use both keyword and embedding
    k=10,
    paper_ids=[1, 2, 3]
)

print(f"Answer: {result['answer']}")
print(f"Sources: {result['num_sources']}")
```

### Example 3: Search all content types

```python
from backend.core.search import search_all

results = search_all(
    query="neural network",
    search_type="keyword",
    limit_per_category=5
)

print(f"Found:")
print(f"  {len(results['papers'])} papers")
print(f"  {len(results['sections'])} sections")
print(f"  {len(results['notes'])} notes")
print(f"  {len(results['summaries'])} summaries")
```

### Example 4: Frontend usage

```typescript
import { ragQuery } from '@/lib/api';

// Hybrid search in RAG
const response = await ragQuery({
  question: "Explain the methodology",
  search_type: "hybrid",
  k: 8,
  paper_ids: [1, 2],
  provider: "openai"
});

console.log("Answer:", response.answer);
console.log("Sources:", response.num_sources);
```

---

## Troubleshooting

### FTS5 Query Errors

If you see errors like `"no such column"`:
- This happens with special characters or hyphens in queries
- The search service automatically wraps phrases in quotes
- Falls back to SQL LIKE search if FTS5 fails

### Empty Search Results

If keyword search returns no results:
- Check that the FTS5 tables are populated
- Verify data exists in the main tables
- Try broader search terms
- Use `"hybrid"` search mode for better coverage

### Embedding Search Issues

If embedding search fails:
- Ensure FAISS index is built: run RAG ingestion
- Check that `sentence-transformers` is installed
- Verify index directory exists at `backend/index/`

---

## Configuration

### Environment Variables

```bash
# Embedding model for FAISS (default: sentence-transformers/all-MiniLM-L6-v2)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Enable/disable image index
ENABLE_IMAGE_INDEX=true

# Image index directory
IMAGE_INDEX_DIR=backend/index_images

# Number of image results
IMAGE_QUERY_K=4
```

### FTS5 Configuration

FTS5 is configured for optimal performance:
- Uses content tables (external content tables)
- Automatic triggers for synchronization
- Proper handling of NULL values
- Relevance ranking with BM25 algorithm

---

## Architecture

### Data Flow

```
User Query
    ↓
API Endpoint (main.py)
    ↓
Search Service (core/search.py)
    ↓
    ├─→ Keyword: FTS5 Query → SQLite
    ├─→ Embedding: Vector Search → FAISS
    └─→ Hybrid: Both → Merge Results
    ↓
Results with Relevance Scores
```

### RAG System Flow

```
User Question
    ↓
RAG Query (rag/query.py)
    ↓
    ├─→ search_type="keyword"
    │       ↓
    │   FTS5 Search → Sections
    │
    ├─→ search_type="embedding"
    │       ↓
    │   FAISS Search → Chunks
    │
    └─→ search_type="hybrid"
            ↓
        Both → Merge
    ↓
Context Chunks
    ↓
LLM Generation
    ↓
Answer with Citations
```

---

## Performance Tips

1. **For specific terms**: Use `"keyword"` search (fastest)
2. **For concepts/meaning**: Use `"embedding"` search
3. **For comprehensive results**: Use `"hybrid"` search
4. **Large datasets**: Keyword search scales better
5. **Small result sets**: Embedding search provides better relevance

---

## Future Enhancements

Potential improvements for the search system:

1. **Ranking**: Combine keyword and embedding scores with weighted ranking
2. **Filters**: Add date range, author, paper type filters
3. **Highlighting**: Return match highlights in search results
4. **Autocomplete**: Suggest search queries based on indexed content
5. **Search history**: Track and save user searches
6. **Advanced queries**: Support boolean operators (AND, OR, NOT)
7. **Fuzzy matching**: Handle typos and variations
8. **Multi-language**: Support non-English documents

---

## Technical Details

### FTS5 Query Handling

The search service handles special characters automatically:

```python
# Phrases with spaces or hyphens are quoted
"machine learning" → '"machine learning"'
"noise-induced" → '"noise-induced"'

# Single words are used as-is
"neural" → 'neural'
```

### Fallback Strategy

If FTS5 search fails, the system automatically falls back to SQL LIKE:

```python
try:
    # Try FTS5
    results = search_with_fts5(query)
except:
    # Fall back to LIKE
    results = search_with_like(query)
```

### Relevance Scoring

- **FTS5**: Uses BM25 ranking algorithm (lower is better)
- **FAISS**: Uses cosine similarity (higher is better)
- **Hybrid**: Preserves original scores from each source

---

## Summary

The hybrid search system provides:

✅ **Flexibility**: Choose the best search mode for your use case
✅ **Performance**: Fast keyword search with FTS5
✅ **Semantics**: Intelligent embedding-based search with FAISS
✅ **Completeness**: Hybrid mode for comprehensive results
✅ **Backward compatible**: All existing APIs continue to work
✅ **Auto-synchronized**: FTS5 tables update automatically

For questions or issues, refer to the test suite in `backend/test_search.py`.
