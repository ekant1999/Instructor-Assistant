from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from ia_phase1.search_hybrid import full_text_search, hybrid_search, reciprocal_rank_fusion


class _FakeConn:
    async def fetch(self, _sql: str, *_params: Any) -> List[Dict[str, Any]]:
        return [
            {
                "id": 11,
                "paper_id": 1,
                "page_no": 2,
                "block_index": 3,
                "text": "keyword hit",
                "bbox": json.dumps({"x0": 1}),
                "metadata": json.dumps({"section_primary": "introduction"}),
                "paper_title": "Paper A",
                "source_url": "https://example.com/a",
                "rank": 0.8,
            }
        ]


class _AcquireCtx:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self) -> _AcquireCtx:
        return _AcquireCtx(self._conn)


class _FakeStore:
    async def similarity_search(
        self,
        _query: str,
        k: int = 10,
        paper_ids=None,
    ) -> List[Dict[str, Any]]:
        _ = (k, paper_ids)
        return [
            {"id": 11, "paper_id": 1, "similarity": 0.91, "text": "vector hit A"},
            {"id": 12, "paper_id": 1, "similarity": 0.77, "text": "vector hit B"},
        ]


def test_reciprocal_rank_fusion_merges_and_scores() -> None:
    vector_results = [
        {"id": 1, "similarity": 0.9, "text": "A"},
        {"id": 2, "similarity": 0.8, "text": "B"},
    ]
    fts_results = [
        {"id": 2, "score": 0.7, "text": "B"},
        {"id": 3, "score": 0.6, "text": "C"},
    ]
    fused = reciprocal_rank_fusion(vector_results, fts_results, k=3, alpha=0.5)
    assert [row["id"] for row in fused] == [2, 1, 3]
    assert all("hybrid_score" in row for row in fused)


def test_full_text_search_parses_json_fields() -> None:
    pool = _FakePool(_FakeConn())
    rows = asyncio.run(full_text_search("planning", pool, k=5))
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == 11
    assert row["bbox"] == {"x0": 1}
    assert row["metadata"] == {"section_primary": "introduction"}
    assert row["source"] == "fts"


def test_hybrid_search_combines_vector_and_fts() -> None:
    pool = _FakePool(_FakeConn())
    store = _FakeStore()
    rows = asyncio.run(hybrid_search("planning", store, pool, k=2, alpha=0.5))
    assert len(rows) == 2
    assert rows[0]["id"] == 11
