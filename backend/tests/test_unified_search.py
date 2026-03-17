from __future__ import annotations

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def test_merge_section_hits_combines_keyword_and_semantic_support() -> None:
    from backend import main as backend_main

    keyword_hits = [
        {
            "id": 101,
            "paper_id": 7,
            "page_no": 2,
            "match_score": 0.20,
            "keyword_score": 0.20,
            "semantic_score": 0.0,
            "lex_hits": 2,
            "exact_phrase": True,
            "match_text": "machine learning improves",
        }
    ]
    semantic_hits = [
        {
            "id": 101,
            "paper_id": 7,
            "page_no": 2,
            "match_score": 0.24,
            "keyword_score": 0.0,
            "semantic_score": 0.24,
            "lex_hits": 1,
            "exact_phrase": False,
        },
        {
            "id": 202,
            "paper_id": 8,
            "page_no": 5,
            "match_score": 0.30,
            "keyword_score": 0.0,
            "semantic_score": 0.30,
            "lex_hits": 0,
            "exact_phrase": False,
        },
    ]

    merged = backend_main._merge_section_hits(keyword_hits, semantic_hits, limit=10)

    assert [item["id"] for item in merged] == [101, 202]
    assert merged[0]["keyword_score"] == 0.20
    assert merged[0]["semantic_score"] == 0.24
    assert merged[0]["match_score"] > merged[1]["match_score"]
    assert merged[0]["match_text"] == "machine learning improves"


def test_aggregate_section_hits_to_papers_rewards_multi_section_support() -> None:
    from backend import main as backend_main

    section_hits = [
        {"id": 1, "paper_id": 10, "page_no": 1, "match_score": 0.42},
        {"id": 2, "paper_id": 10, "page_no": 2, "match_score": 0.31},
        {"id": 3, "paper_id": 11, "page_no": 1, "match_score": 0.50},
    ]

    aggregated = backend_main._aggregate_section_hits_to_papers(section_hits, {10: 0.03, 11: 0.0})

    assert aggregated[10]["best_hit"]["id"] == 1
    assert aggregated[10]["support_hits"][1]["id"] == 2
    assert aggregated[10]["title_bonus"] == 0.03
    assert aggregated[10]["score"] > aggregated[11]["score"]


def test_aggregate_section_hits_to_papers_keeps_ranking_best_hit() -> None:
    from backend import main as backend_main

    section_hits = [
        {
            "id": 1,
            "paper_id": 10,
            "page_no": 1,
            "match_score": 0.22,
            "lex_hits": 3,
            "search_bucket": "body",
            "match_section_canonical": "abstract",
            "source_text": "This benchmark improves evaluation quality for scientific documents.",
        },
        {
            "id": 2,
            "paper_id": 10,
            "page_no": 6,
            "match_score": 0.18,
            "lex_hits": 3,
            "search_bucket": "body",
            "match_section_canonical": "experiments",
            "source_text": "Evaluation benchmark results and experiments are reported here.",
        },
    ]

    aggregated = backend_main._aggregate_section_hits_to_papers(
        section_hits,
        {10: 0.0},
    )

    assert aggregated[10]["ranking_best_hit"]["id"] == 1
    assert aggregated[10]["best_hit"]["id"] == 1


def test_search_section_hits_unified_merges_both_channels(monkeypatch) -> None:
    from backend import main as backend_main

    monkeypatch.setattr(
        backend_main,
        "_keyword_section_hits",
        lambda *args, **kwargs: [
            {
                "id": 51,
                "paper_id": 5,
                "page_no": 3,
                "match_score": 0.18,
                "keyword_score": 0.18,
                "semantic_score": 0.0,
                "lex_hits": 2,
                "exact_phrase": True,
            }
        ],
    )
    monkeypatch.setattr(
        backend_main,
        "_pgvector_search_section_hits",
        lambda *args, **kwargs: [
            {
                "id": 51,
                "paper_id": 5,
                "page_no": 3,
                "match_score": 0.22,
                "keyword_score": 0.0,
                "semantic_score": 0.22,
                "lex_hits": 1,
                "exact_phrase": False,
            }
        ],
    )

    hits = backend_main._search_section_hits_unified(
        "vision language model",
        "hybrid",
        paper_ids=None,
        include_text=False,
        max_chars=None,
        limit=20,
    )

    assert len(hits) == 1
    assert hits[0]["id"] == 51
    assert hits[0]["match_score"] > 0.40


def test_infer_search_section_bucket_detects_references_and_front_matter() -> None:
    from backend import main as backend_main

    references_text = "References\n[1] A. Author. Proceedings of the Conference, 2024. [2] B. Author. Journal, 2023."
    front_matter_text = "Title of Paper\nAlice University\nbob@example.edu\nAbstract\nWe study..."

    assert backend_main._infer_search_section_bucket(references_text, page_no=9) == "references"
    assert backend_main._infer_search_section_bucket(front_matter_text, page_no=1) == "front_matter"
    assert backend_main._infer_search_section_bucket("Method overview and results discussion", page_no=3) == "body"


def test_reference_hits_are_penalized_in_paper_aggregation() -> None:
    from backend import main as backend_main

    section_hits = [
        {
            "id": 1,
            "paper_id": 10,
            "page_no": 11,
            "match_score": 0.90 * backend_main._section_bucket_multiplier("references"),
            "search_bucket": "references",
        },
        {
            "id": 4,
            "paper_id": 10,
            "page_no": 12,
            "match_score": 0.70 * backend_main._section_bucket_multiplier("references"),
            "search_bucket": "references",
        },
        {
            "id": 2,
            "paper_id": 11,
            "page_no": 3,
            "match_score": 0.55 * backend_main._section_bucket_multiplier("body"),
            "search_bucket": "body",
        },
    ]

    aggregated = backend_main._aggregate_section_hits_to_papers(section_hits)

    assert aggregated[11]["score"] > aggregated[10]["score"]


def test_filter_section_hits_for_query_rejects_weak_reference_and_semantic_only_hits() -> None:
    from backend import main as backend_main

    hits = [
        {
            "id": 1,
            "paper_id": 10,
            "page_no": 9,
            "match_score": 0.04,
            "keyword_score": 0.04,
            "semantic_score": 0.0,
            "semantic_raw_score": 0.0,
            "block_match_score": 0.0,
            "lex_hits": 1,
            "exact_phrase": False,
            "search_bucket": "references",
            "source_text": "References [1] benchmark paper 2024",
        },
        {
            "id": 2,
            "paper_id": 11,
            "page_no": 3,
            "match_score": 0.073,
            "keyword_score": 0.0,
            "semantic_score": 0.053,
            "semantic_raw_score": 0.009,
            "block_match_score": 3.5,
            "lex_hits": 2,
            "exact_phrase": False,
            "search_bucket": "body",
            "source_text": "This result improves prediction quality on the benchmark.",
        },
        {
            "id": 3,
            "paper_id": 12,
            "page_no": 2,
            "match_score": 0.12,
            "keyword_score": 0.0,
            "semantic_score": 0.0,
            "semantic_raw_score": 0.0,
            "block_match_score": 5.4,
            "lex_hits": 3,
            "exact_phrase": False,
            "search_bucket": "body",
            "source_text": "A scientific multimodal benchmark for document reasoning.",
        },
    ]

    filtered = backend_main._filter_section_hits_for_query("scientific multimodal benchmark", hits)

    assert [item["id"] for item in filtered] == [3]


def test_filter_aggregated_papers_for_query_rejects_papers_without_credible_support() -> None:
    from backend import main as backend_main

    aggregated = {
        10: {
            "score": 0.22,
            "best_hit": {
                "id": 1,
                "paper_id": 10,
                "page_no": 3,
                "search_bucket": "body",
                "lex_hits": 2,
                "exact_phrase": False,
                "semantic_raw_score": 0.009,
                "block_match_score": 3.5,
                "match_score": 0.073,
                "source_text": "This result improves prediction quality on the benchmark.",
            },
            "support_hits": [
                {
                    "id": 1,
                    "paper_id": 10,
                    "page_no": 3,
                    "search_bucket": "body",
                    "lex_hits": 2,
                    "exact_phrase": False,
                    "semantic_raw_score": 0.009,
                    "block_match_score": 3.5,
                    "match_score": 0.073,
                    "source_text": "This result improves prediction quality on the benchmark.",
                }
            ],
            "title_bonus": 0.0,
        },
        11: {
            "score": 0.25,
            "best_hit": {
                "id": 2,
                "paper_id": 11,
                "page_no": 2,
                "search_bucket": "body",
                "lex_hits": 3,
                "exact_phrase": False,
                "semantic_raw_score": 0.0,
                "block_match_score": 5.4,
                "source_text": "A multimodal benchmark for scientific document reasoning.",
            },
            "support_hits": [
                {
                    "id": 2,
                    "paper_id": 11,
                    "page_no": 2,
                    "search_bucket": "body",
                    "lex_hits": 3,
                    "exact_phrase": False,
                    "semantic_raw_score": 0.0,
                    "block_match_score": 5.4,
                    "source_text": "A multimodal benchmark for scientific document reasoning.",
                }
            ],
            "title_bonus": 0.0,
        },
    }

    filtered = backend_main._filter_aggregated_papers_for_query("scientific multimodal benchmark", aggregated)

    assert list(filtered.keys()) == [11]


def test_filter_aggregated_papers_for_query_rejects_low_salience_sole_support() -> None:
    from backend import main as backend_main

    aggregated = {
        7: {
            "score": 0.30,
            "best_hit": {
                "id": 12,
                "paper_id": 7,
                "page_no": 6,
                "search_bucket": "body",
                "match_section_canonical": "experimental_protocol",
                "lex_hits": 4,
                "exact_phrase": False,
                "semantic_raw_score": 0.015,
                "block_match_score": 7.0,
                "match_score": 0.10,
                "source_text": "The generated code passes all unit tests in the coding evaluation setup.",
            },
            "support_hits": [
                {
                    "id": 12,
                    "paper_id": 7,
                    "page_no": 6,
                    "search_bucket": "body",
                    "match_section_canonical": "experimental_protocol",
                    "lex_hits": 4,
                    "exact_phrase": False,
                    "semantic_raw_score": 0.015,
                    "block_match_score": 7.0,
                    "match_score": 0.10,
                    "source_text": "The generated code passes all unit tests in the coding evaluation setup.",
                }
            ],
            "title_bonus": 0.0,
        }
    }

    filtered = backend_main._filter_aggregated_papers_for_query("code generation from unit tests", aggregated)

    assert filtered == {}


def test_inject_title_only_candidates_rescues_strong_title_match(monkeypatch) -> None:
    from backend import main as backend_main

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *_args, **_kwargs):
            class _Rows:
                def fetchall(self_nonlocal):
                    return [
                        {
                            "id": 301,
                            "paper_id": 42,
                            "page_no": 1,
                            "text": "Introductory page text.",
                        }
                    ]

            return _Rows()

    monkeypatch.setattr(backend_main, "get_conn", lambda: _FakeConn())

    aggregated = backend_main._inject_title_only_candidates({}, {42: 0.35, 43: 0.18})

    assert list(aggregated.keys()) == [42]
    assert aggregated[42]["title_only_match"] is True
    assert aggregated[42]["score"] == 0.35
    assert aggregated[42]["best_hit"]["page_no"] == 1


def test_filter_section_hits_for_query_ignores_stopword_heavy_overlap() -> None:
    from backend import main as backend_main

    hits = [
        {
            "id": 1,
            "paper_id": 10,
            "page_no": 6,
            "match_score": 0.073,
            "keyword_score": 0.0,
            "semantic_score": 0.053,
            "semantic_raw_score": 0.008,
            "block_match_score": 3.5,
            "lex_hits": 2,
            "exact_phrase": False,
            "search_bucket": "body",
            "source_text": "Two datasets relate to the emotion understanding task.",
        },
        {
            "id": 2,
            "paper_id": 11,
            "page_no": 2,
            "match_score": 0.094,
            "keyword_score": 0.0,
            "semantic_score": 0.064,
            "semantic_raw_score": 0.013,
            "block_match_score": 6.0,
            "lex_hits": 4,
            "exact_phrase": False,
            "search_bucket": "body",
            "source_text": "Audio speech emotion recognition with contrastive learning.",
        },
    ]

    filtered = backend_main._filter_section_hits_for_query("speech emotion recognition from audio", hits)

    assert [item["id"] for item in filtered] == [2]


def test_rerank_section_hits_for_localization_prefers_methodology_for_method_query() -> None:
    from backend import main as backend_main

    reranked = backend_main._rerank_section_hits_for_localization(
        "feature matching method",
        [
            {
                "id": 1,
                "paper_id": 7,
                "page_no": 1,
                "match_score": 0.16,
                "lex_hits": 2,
                "search_bucket": "body",
                "match_section_canonical": "abstract",
                "source_text": "We study a feature matching method for language models.",
            },
            {
                "id": 2,
                "paper_id": 7,
                "page_no": 4,
                "match_score": 0.14,
                "lex_hits": 2,
                "search_bucket": "body",
                "match_section_canonical": "methodology",
                "source_text": "Our method uses feature matching objectives and block-parallel rollouts.",
            },
        ],
    )

    assert reranked[0]["id"] == 2
    assert reranked[0]["localization_score"] > reranked[1]["localization_score"]


def test_search_paper_sections_for_localization_prefers_evaluation_section(monkeypatch) -> None:
    from backend import main as backend_main

    monkeypatch.setattr(
        backend_main,
        "_keyword_section_hits",
        lambda *args, **kwargs: [
            {
                "id": 1,
                "paper_id": 10,
                "page_no": 1,
                "match_score": 0.22,
                "keyword_score": 0.22,
                "semantic_score": 0.0,
                "lex_hits": 3,
                "search_bucket": "body",
                "match_section_canonical": "abstract",
                "source_text": "This benchmark improves evaluation quality for scientific documents.",
            },
            {
                "id": 2,
                "paper_id": 10,
                "page_no": 6,
                "match_score": 0.18,
                "keyword_score": 0.18,
                "semantic_score": 0.0,
                "lex_hits": 3,
                "search_bucket": "body",
                "match_section_canonical": "experiments",
                "source_text": "Evaluation benchmark results and experiments are reported here.",
            },
        ],
    )
    monkeypatch.setattr(backend_main, "_pgvector_search_section_hits", lambda *args, **kwargs: [])

    hits = backend_main._search_paper_sections_for_localization(
        "evaluation benchmark results",
        "hybrid",
        10,
        include_text=False,
        max_chars=None,
        limit=20,
    )

    assert hits[0]["match_section_canonical"] == "experiments"


def test_list_papers_reuses_cached_response(monkeypatch) -> None:
    from backend import main as backend_main
    from backend.core.search_cache import clear_search_caches

    clear_search_caches()
    calls = {"search": 0}

    def _search(*_args, **_kwargs):
        calls["search"] += 1
        return []

    monkeypatch.setattr(backend_main, "current_search_index_version", lambda: 41)
    monkeypatch.setattr(backend_main, "_search_section_hits_unified", _search)
    monkeypatch.setattr(backend_main, "_filter_section_hits_for_query", lambda query, hits: hits)
    monkeypatch.setattr(backend_main, "_paper_title_bonus_lookup", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(backend_main, "_aggregate_section_hits_to_papers", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(backend_main, "_inject_title_only_candidates", lambda aggregated, *_args, **_kwargs: aggregated)
    monkeypatch.setattr(backend_main, "_filter_aggregated_papers_for_query", lambda *_args, **_kwargs: {})

    first = backend_main.list_papers(q="LLM", search_type="hybrid")
    second = backend_main.list_papers(q="LLM", search_type="hybrid")

    assert first == {"papers": []}
    assert second == first
    assert calls["search"] == 1


def test_list_paper_sections_cache_invalidates_on_version_change(monkeypatch) -> None:
    from backend import main as backend_main
    from backend.core.search_cache import clear_search_caches

    clear_search_caches()
    state = {"version": 7, "calls": 0}

    class _FakeRows:
        def fetchone(self):
            return {"id": 9}

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *_args, **_kwargs):
            return _FakeRows()

    def _search(*_args, **_kwargs):
        state["calls"] += 1
        return [{"id": state["calls"], "paper_id": 9, "page_no": 2, "match_text": "cached hit"}]

    monkeypatch.setattr(backend_main, "get_conn", lambda: _FakeConn())
    monkeypatch.setattr(backend_main, "current_search_index_version", lambda: state["version"])
    monkeypatch.setattr(backend_main, "_search_paper_sections_for_localization", _search)

    first = backend_main.list_paper_sections(9, q="planning", search_type="hybrid")
    second = backend_main.list_paper_sections(9, q="planning", search_type="hybrid")
    state["version"] = 8
    third = backend_main.list_paper_sections(9, q="planning", search_type="hybrid")

    assert first["sections"][0]["id"] == 1
    assert second == first
    assert third["sections"][0]["id"] == 2
    assert state["calls"] == 2
