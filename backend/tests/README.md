# pgvector Tests

This directory contains tests for the pgvector migration.

## Test Categories

### Unit Tests (`test_pgvector.py`)
- Embedding generation
- Vector insertion and retrieval
- Hybrid search accuracy
- Block-level location tracking
- PDF parsing with PyMuPDF

### Integration Tests (`test_migration.py`)
- SQLite → PostgreSQL data migration
- Data integrity verification
- Relationship preservation
- Search quality comparison

### Performance Benchmarks (`test_performance.py`)
- Query latency (p50, p95, p99)
- Index build time
- Concurrent query handling
- Scalability tests

## Setup

### 1. Install Test Dependencies

```bash
pip install pytest pytest-asyncio
```

### 2. Configure Test Environment

Create a test `.env` file or export variables:

```bash
export DATABASE_URL=postgresql://instructor:password@localhost:5432/instructor_assistant_test
```

### 3. Setup Test Database

```bash
# Create test database
psql -U postgres -c "CREATE DATABASE instructor_assistant_test OWNER instructor;"

# Initialize schema
python -c "import asyncio; from backend.core.postgres import init_db; asyncio.run(init_db())"
```

## Running Tests

### Run All Tests

```bash
# From backend directory
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/test_pgvector.py -v

# Integration tests only
pytest tests/test_migration.py -v

# Performance benchmarks only
pytest tests/test_performance.py -v -m benchmark
```

### Run with Coverage

```bash
pytest tests/ --cov=backend --cov-report=html
```

## Test Requirements

Some tests require:
- PostgreSQL with pgvector extension running
- `DATABASE_URL` environment variable set
- Sample data in the database
- Sample PDF files in `tests/fixtures/` (for PDF parsing tests)

Tests will automatically skip if requirements are not met.

## Interpreting Results

### Unit Tests
All unit tests should pass. Failures indicate bugs in core functionality.

### Integration Tests
- **test_migration_preserves_papers**: Verifies paper count matches
- **test_migration_preserves_relationships**: Checks foreign keys are valid
- **test_text_blocks_have_location_data**: Validates block metadata

### Performance Benchmarks
Expected performance targets:

| Metric | Target | Good | Acceptable |
|--------|--------|------|------------|
| Vector search p95 | <100ms | <200ms | <500ms |
| Hybrid search avg | <200ms | <500ms | <1000ms |
| Concurrent queries (10) | <1s | <3s | <5s |
| Embedding generation | >50 texts/sec | >20 texts/sec | >10 texts/sec |

## Continuous Integration

To run tests in CI:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: instructor
          POSTGRES_PASSWORD: password
          POSTGRES_DB: instructor_assistant_test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://instructor:password@localhost:5432/instructor_assistant_test
        run: |
          cd backend
          pytest tests/ -v --cov=backend
```

## Troubleshooting

### "DATABASE_URL not configured"
Set the environment variable:
```bash
export DATABASE_URL=postgresql://user:pass@host:5432/db
```

### "No data to benchmark"
Run ingestion before performance tests:
```bash
python backend/rag/ingest_pgvector.py
```

### "Sample PDF not found"
Create `tests/fixtures/` directory and add sample PDF:
```bash
mkdir -p tests/fixtures
# Add a sample.pdf file
```

### Tests are slow
1. Use test database (don't test on production data)
2. Reduce dataset size for tests
3. Run benchmarks separately with `-m benchmark`

## Adding New Tests

When adding new tests:

1. Follow naming convention: `test_*.py`
2. Use descriptive test function names: `test_feature_does_something`
3. Add docstrings explaining what the test validates
4. Use `pytest.skip()` for tests requiring special setup
5. Mark slow tests with `@pytest.mark.benchmark`
6. Clean up test data (use fixtures or manual cleanup)

Example:

```python
@pytest.mark.asyncio
async def test_new_feature(self):
    """Test that new feature works correctly."""
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = await feature_function(setup_data)
    
    # Assert
    assert result.success
    assert result.value == expected_value
    
    # Cleanup
    await cleanup_test_data()
```
