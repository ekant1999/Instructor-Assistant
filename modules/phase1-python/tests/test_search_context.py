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


def test_select_block_for_query_returns_phrase_bbox_when_line_spans_exist() -> None:
    row = {
        "page_no": 1,
        "block_index": 1,
        "bbox": {"x0": 0, "y0": 0, "x1": 200, "y1": 80},
        "text": "fallback",
        "metadata": {
            "blocks": [
                {
                    "page_no": 1,
                    "block_index": 1,
                    "bbox": {"x0": 0, "y0": 0, "x1": 200, "y1": 80},
                    "text": "We use prompt tuning for robust adaptation.",
                    "metadata": {
                        "section_canonical": "method",
                        "lines": [
                            {
                                "text": "We use prompt tuning for robust adaptation.",
                                "bbox": {"x0": 0, "y0": 0, "x1": 200, "y1": 20},
                                "spans": [
                                    {"text": "We use", "bbox": {"x0": 0, "y0": 0, "x1": 40, "y1": 20}},
                                    {"text": "prompt", "bbox": {"x0": 50, "y0": 0, "x1": 90, "y1": 20}},
                                    {"text": "tuning", "bbox": {"x0": 95, "y0": 0, "x1": 135, "y1": 20}},
                                    {"text": "for robust adaptation.", "bbox": {"x0": 145, "y0": 0, "x1": 200, "y1": 20}},
                                ],
                            }
                        ],
                    },
                }
            ],
        },
    }
    best = select_block_for_query(row, ["prompt", "tuning"], query="prompt tuning")
    assert best["block_index"] == 1
    assert best["bbox"] == {"x0": 50.0, "y0": 0.0, "x1": 135.0, "y1": 20.0}


def test_select_block_for_query_falls_back_to_best_line_bbox_when_phrase_is_split() -> None:
    row = {
        "page_no": 2,
        "block_index": 3,
        "bbox": {"x0": 0, "y0": 0, "x1": 200, "y1": 100},
        "text": "fallback",
        "metadata": {
            "blocks": [
                {
                    "page_no": 2,
                    "block_index": 3,
                    "bbox": {"x0": 0, "y0": 0, "x1": 200, "y1": 100},
                    "text": "We study infeasible states.\nAdditional details follow below.",
                    "metadata": {
                        "section_canonical": "results",
                        "lines": [
                            {
                                "text": "We study infeasible states.",
                                "bbox": {"x0": 0, "y0": 0, "x1": 160, "y1": 16},
                                "spans": [
                                    {"text": "We study", "bbox": {"x0": 0, "y0": 0, "x1": 48, "y1": 16}},
                                    {"text": "infeasible", "bbox": {"x0": 56, "y0": 0, "x1": 108, "y1": 16}},
                                    {"text": "states.", "bbox": {"x0": 116, "y0": 0, "x1": 160, "y1": 16}},
                                ],
                            },
                            {
                                "text": "Additional details follow below.",
                                "bbox": {"x0": 0, "y0": 20, "x1": 180, "y1": 36},
                                "spans": [
                                    {"text": "Additional details follow below.", "bbox": {"x0": 0, "y0": 20, "x1": 180, "y1": 36}},
                                ],
                            },
                        ],
                    },
                }
            ],
        },
    }
    best = select_block_for_query(row, ["infeasible"], query="infeasible")
    assert best["bbox"] == {"x0": 56.0, "y0": 0.0, "x1": 108.0, "y1": 16.0}


def test_select_block_for_query_slices_single_span_bbox_for_short_phrase() -> None:
    row = {
        "page_no": 1,
        "block_index": 5,
        "bbox": {"x0": 0, "y0": 0, "x1": 220, "y1": 18},
        "text": "fallback",
        "metadata": {
            "blocks": [
                {
                    "page_no": 1,
                    "block_index": 5,
                    "bbox": {"x0": 0, "y0": 0, "x1": 220, "y1": 18},
                    "text": "We use prompt tuning for robust adaptation.",
                    "metadata": {
                        "section_canonical": "method",
                        "lines": [
                            {
                                "text": "We use prompt tuning for robust adaptation.",
                                "bbox": {"x0": 0, "y0": 0, "x1": 220, "y1": 18},
                                "spans": [
                                    {
                                        "text": "We use prompt tuning for robust adaptation.",
                                        "bbox": {"x0": 0, "y0": 0, "x1": 220, "y1": 18},
                                    }
                                ],
                            }
                        ],
                    },
                }
            ],
        },
    }
    best = select_block_for_query(row, ["prompt", "tuning"], query="prompt tuning")
    bbox = best["bbox"]
    assert bbox["y0"] == 0.0
    assert bbox["y1"] == 18.0
    assert 0.0 < bbox["x0"] < bbox["x1"] < 220.0
