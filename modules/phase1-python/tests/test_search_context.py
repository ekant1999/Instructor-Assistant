from __future__ import annotations

from ia_phase1.search_context import (
    build_match_snippet,
    pgvector_score,
    query_tokens,
    select_block_for_query,
)


def test_query_tokens_deduplicates_and_filters_short_terms() -> None:
    tokens = query_tokens("We define one-shot and then sequential planning planning")
    assert tokens == ["define", "one", "shot", "and", "then", "sequential", "planning"]


def test_pgvector_score_uses_first_available_numeric_field() -> None:
    assert pgvector_score({"hybrid_score": 0.7, "similarity": 0.9}) == 0.7
    assert pgvector_score({"similarity": "0.42"}) == 0.42
    assert pgvector_score({"score": 1}) == 1.0
    assert pgvector_score({}) == 0.0


def test_select_block_for_query_prefers_best_lexical_hit() -> None:
    row = {
        "page_no": 2,
        "block_index": 9,
        "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
        "text": "fallback text",
        "metadata": {
            "section_primary": "related_work",
            "blocks": [
                {
                    "page_no": 2,
                    "block_index": 3,
                    "text": "This paragraph is unrelated.",
                    "metadata": {"section_canonical": "related_work"},
                },
                {
                    "page_no": 2,
                    "block_index": 4,
                    "text": "We define one-shot and then sequential planning as a process.",
                    "metadata": {"section_canonical": "problem_definition"},
                },
            ],
        },
    }
    best = select_block_for_query(
        row,
        ["define", "one", "shot", "sequential", "planning"],
        query="We define one-shot and then sequential planning",
    )
    assert best["block_index"] == 4
    assert best["section_canonical"] == "problem_definition"
    assert best["lex_hits"] >= 4


def test_select_block_for_query_prefers_exact_phrase_over_token_overlap() -> None:
    row = {
        "page_no": 2,
        "block_index": 7,
        "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
        "text": "fallback text",
        "metadata": {
            "section_primary": "related_work",
            "blocks": [
                {
                    "page_no": 2,
                    "block_index": 3,
                    "text": "We define planning sequentially and compare planning methods broadly.",
                    "metadata": {"section_canonical": "related_work"},
                },
                {
                    "page_no": 2,
                    "block_index": 4,
                    "text": "We define one-shot and then sequential planning as a process of solving tasks.",
                    "metadata": {"section_canonical": "problem_definition"},
                },
            ],
        },
    }
    best = select_block_for_query(
        row,
        ["define", "one", "shot", "sequential", "planning"],
        query="We define one-shot and then sequential planning",
    )
    assert best["block_index"] == 4
    assert best["section_canonical"] == "problem_definition"
    assert bool(best.get("exact_phrase"))


def test_select_block_for_query_keeps_zero_block_index() -> None:
    row = {
        "page_no": 5,
        "block_index": 19,
        "bbox": {"x0": 0, "y0": 0, "x1": 10, "y1": 10},
        "text": "fallback",
        "metadata": {
            "blocks": [
                {
                    "page_no": 5,
                    "block_index": 0,
                    "text": "Exact phrase appears here.",
                    "metadata": {"section_canonical": "abstract"},
                }
            ],
        },
    }
    best = select_block_for_query(row, ["exact", "phrase"], query="Exact phrase appears")
    assert best["block_index"] == 0
    assert best["section_canonical"] == "abstract"


def test_build_match_snippet_contains_query_focus() -> None:
    text = (
        "Intro text. We consider several settings. "
        "We define one-shot and then sequential planning as a process of solving related problems. "
        "Additional details follow."
    )
    tokens = query_tokens("one-shot sequential planning")
    snippet = build_match_snippet("one-shot sequential planning", tokens, text, max_len=120)
    lower = snippet.lower()
    assert "sequential planning" in lower
    assert len(snippet) <= 120
