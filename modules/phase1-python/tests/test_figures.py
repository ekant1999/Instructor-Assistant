from __future__ import annotations

from pathlib import Path

import pytest

from ia_phase1.figures import (
    extract_and_store_paper_figures,
    load_paper_figure_manifest,
    resolve_figure_file,
)
from ia_phase1.parser import extract_text_blocks


def test_extract_figures_from_text_only_pdf(
    sample_pdf: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("FIGURE_VECTOR_ENABLED", "false")
    blocks = extract_text_blocks(sample_pdf)

    payload = extract_and_store_paper_figures(sample_pdf, paper_id=31, blocks=blocks)
    assert payload["paper_id"] == 31
    assert payload["num_images"] == 0

    manifest = load_paper_figure_manifest(31)
    assert manifest["num_images"] == 0
    assert manifest["images"] == []


def test_load_figure_manifest_missing_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path))
    payload = load_paper_figure_manifest(404)
    assert payload["paper_id"] == 404
    assert payload["num_images"] == 0
    assert payload["images"] == []


def test_resolve_figure_file_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        resolve_figure_file(1, "../escape.png")
