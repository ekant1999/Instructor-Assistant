from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from ia_phase1.tables import (
    _append_or_replace_table_record,
    _build_caption_guided_text_candidates,
    _caption_block_match_score,
    _find_nearest_caption_block,
    _looks_like_explicit_table_caption,
    _looks_like_false_positive_table,
    _materialize_table_record,
    _missing_explicit_table_caption_indices,
    _merge_sparse_pre_numeric_text_columns,
    _pick_headers_and_rows,
    _repair_leading_text_fragment_columns,
    _repair_headers_from_auxiliary_band,
    _resolve_candidate_caption_binding,
    extract_and_store_paper_tables,
    load_paper_table_manifest,
    table_records_to_chunks,
)


def test_extract_tables_returns_empty_when_disabled(
    sample_pdf: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_EXTRACTION_ENABLED", "false")
    payload = extract_and_store_paper_tables(sample_pdf, paper_id=77, blocks=[])
    assert payload["paper_id"] == 77
    assert payload["num_tables"] == 0
    assert payload["tables"] == []


def test_table_records_to_chunks_builds_table_metadata() -> None:
    tables = [
        {
            "id": 1,
            "page_no": 2,
            "caption": "Table 1: Results",
            "n_rows": 2,
            "n_cols": 3,
            "headers": ["Model", "PSNR", "SSIM"],
            "rows": [["A", "30.1", "0.92"], ["B", "31.2", "0.94"]],
            "bbox": {"x0": 10, "y0": 10, "x1": 400, "y1": 200},
            "section_canonical": "experiments",
            "section_title": "Experiments",
            "section_source": "pdf_toc",
            "section_confidence": 0.97,
        }
    ]
    text_blocks = [{"page_no": 2, "block_index": 4, "text": "context", "bbox": None, "metadata": {}}]
    chunks = table_records_to_chunks(tables=tables, text_blocks=text_blocks)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert "Table 1: Results" in chunk["text"]
    assert chunk["metadata"]["content_type"] == "table"
    assert chunk["metadata"]["section_primary"] == "experiments"
    assert chunk["metadata"]["table_total_cols"] == 3


def test_load_table_manifest_missing_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path))
    payload = load_paper_table_manifest(9999)
    assert payload["paper_id"] == 9999
    assert payload["num_tables"] == 0
    assert payload["tables"] == []


def test_load_table_manifest_reads_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path))
    paper_dir = tmp_path / "12"
    paper_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "paper_id": 12,
        "num_tables": 1,
        "tables": [{"id": 1, "caption": "Table 1"}],
    }
    (paper_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    payload = load_paper_table_manifest(12)
    assert payload["paper_id"] == 12
    assert payload["num_tables"] == 1
    assert payload["tables"][0]["id"] == 1


def _build_ruled_table_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 56), "Table 1. Example results")
    x0, y0 = 72, 88
    width, height = 240, 96
    rows, cols = 3, 3
    for row_idx in range(rows + 1):
        y = y0 + (row_idx * height / rows)
        page.draw_line((x0, y), (x0 + width, y))
    for col_idx in range(cols + 1):
        x = x0 + (col_idx * width / cols)
        page.draw_line((x, y0), (x, y0 + height))

    labels = [["Model", "PSNR", "SSIM"], ["A", "30.1", "0.92"], ["B", "31.2", "0.94"]]
    for row_idx, row in enumerate(labels):
        for col_idx, text in enumerate(row):
            page.insert_text((x0 + 10 + col_idx * width / cols, y0 + 18 + row_idx * height / rows), text)
    doc.save(str(path))
    doc.close()


def _build_caption_plus_prose_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((72, 72, 500, 100), "Table 1. Performance comparison across models.", fontsize=12)
    prose = ("This paragraph discusses the results in prose and should not be extracted as a table. " * 8).strip()
    page.insert_textbox((72, 120, 520, 260), prose, fontsize=11)
    doc.save(str(path))
    doc.close()


def _build_borderless_numeric_table_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox((72, 72, 520, 98), "Table 1. Long-context benchmark results.", fontsize=12)

    x_positions = [90, 190, 280, 360, 440]
    headers = ["Method", "1K", "2K", "4K", "8K"]
    rows = [
        ["Base", "72.1", "70.4", "68.0", "61.3"],
        ["Memory", "79.8", "78.2", "75.1", "70.9"],
        ["Memory+", "81.2", "80.1", "78.4", "74.0"],
    ]
    y = 126
    for idx, text in enumerate(headers):
        page.insert_text((x_positions[idx], y), text, fontsize=10)
    y += 20
    for row in rows:
        for idx, text in enumerate(row):
            page.insert_text((x_positions[idx], y), text, fontsize=10)
        y += 18

    doc.save(str(path))
    doc.close()


def test_extract_tables_uses_native_pymupdf_detection_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "ruled_table.pdf"
    _build_ruled_table_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.delenv("TABLE_TEXT_FALLBACK_ENABLED", raising=False)

    payload = extract_and_store_paper_tables(pdf_path, paper_id=88, blocks=[])

    assert payload["num_tables"] == 1
    table = payload["tables"][0]
    assert table["detection_strategy"] in {"pymupdf_native", "pymupdf_lines_strict"}
    # Native PyMuPDF markdown omits the padded cells our fallback renderer adds.
    assert table["markdown"].startswith("|Model|PSNR|SSIM|")
    assert table["headers"] == ["Model", "PSNR", "SSIM"]
    assert table["rows"] == [["A", "30.1", "0.92"], ["B", "31.2", "0.94"]]


def test_extract_tables_does_not_promote_caption_plus_prose_to_table_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "caption_prose.pdf"
    _build_caption_plus_prose_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.delenv("TABLE_TEXT_FALLBACK_ENABLED", raising=False)

    payload = extract_and_store_paper_tables(pdf_path, paper_id=89, blocks=[])

    assert payload["num_tables"] == 0


def test_extract_tables_auto_text_fallback_recovers_caption_backed_borderless_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "borderless_numeric_table.pdf"
    _build_borderless_numeric_table_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.delenv("TABLE_TEXT_FALLBACK_ENABLED", raising=False)
    monkeypatch.delenv("TABLE_AUTO_TEXT_FALLBACK_ENABLED", raising=False)

    payload = extract_and_store_paper_tables(pdf_path, paper_id=91, blocks=[])

    assert payload["num_tables"] == 1
    table = payload["tables"][0]
    assert table["detection_strategy"] == "text_caption_fallback"
    assert "Table 1." in table["caption"]
    assert table["n_cols"] >= 5
    assert table["n_rows"] >= 3


def test_caption_guided_candidates_merge_native_row_fragments_for_above_caption_tables() -> None:
    caption_blocks = [
        {
            "text": "Table 5: Detailed dataset statistics.",
            "bbox": {"x0": 72.0, "y0": 220.0, "x1": 523.0, "y1": 244.0},
        }
    ]
    lines_tables = [
        _FakeExtractTable((72.0, 110.0, 523.0, 130.0), [["Dataset", "Task", "Description", "Train", "Test", "Metric"]]),
        _FakeExtractTable((72.0, 150.0, 523.0, 170.0), [["NQ", "QA", "Open-domain", "79168", "3610", "EM"]]),
        _FakeExtractTable((72.0, 190.0, 523.0, 210.0), [["FEVER", "Fact", "Verification", "145449", "19998", "Acc"]]),
    ]
    page = _FakeCaptionGuidedPage(
        text_blocks=[
            {
                "type": 0,
                "bbox": (72.0, 220.0, 523.0, 244.0),
                "lines": [{"spans": [{"text": "Table 5: Detailed dataset statistics."}]}],
            }
        ],
        lines_tables=lines_tables,
        text_tables=[],
    )

    candidates = _build_caption_guided_text_candidates(
        page,
        caption_blocks,
        min_area=1000.0,
        min_cols=2,
        caption_indices={0},
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["detection_strategy"] == "caption_guided_native"
    assert candidate["raw_row_count"] == 3
    assert candidate["bbox"]["y1"] <= caption_blocks[0]["bbox"]["y0"]


def test_caption_guided_candidates_do_not_steal_previous_same_column_table_body() -> None:
    caption_blocks = [
        {
            "text": "Table 1: First table.",
            "bbox": {"x0": 108.0, "y0": 70.0, "x1": 505.0, "y1": 126.0},
        },
        {
            "text": "Table 2: Second table.",
            "bbox": {"x0": 108.0, "y0": 223.0, "x1": 505.0, "y1": 257.0},
        },
    ]
    above_candidate = _FakeExtractTable(
        (114.0, 136.0, 498.0, 209.0),
        [["Method", "1K", "2K"], ["Base", "72.1", "70.4"], ["Memory", "79.8", "78.2"]],
    )
    below_candidate = _FakeExtractTable(
        (108.0, 267.0, 504.0, 520.0),
        [["Method", "16K", "32K"], ["Base", "52.5", "9.4"], ["MemDLM", "55.3", "10.3"]],
    )

    def find_tables_fn(*, strategy, clip):
        if strategy != "text" or clip is None:
            return []
        _, y0, _, y1 = clip
        if y1 <= 223.0:
            return [above_candidate]
        if y0 >= 257.0:
            return [below_candidate]
        return []

    page = _FakeCaptionGuidedPage(
        text_blocks=[
            {
                "type": 0,
                "bbox": (108.0, 70.0, 505.0, 126.0),
                "lines": [{"spans": [{"text": "Table 1: First table."}]}],
            },
            {
                "type": 0,
                "bbox": (108.0, 223.0, 505.0, 257.0),
                "lines": [{"spans": [{"text": "Table 2: Second table."}]}],
            },
        ],
        find_tables_fn=find_tables_fn,
    )

    candidates = _build_caption_guided_text_candidates(
        page,
        caption_blocks,
        min_area=1000.0,
        min_cols=2,
        caption_indices={1},
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["seed_caption_id"] == 1
    assert candidate["bbox"]["y0"] >= caption_blocks[1]["bbox"]["y1"]


def test_extract_tables_text_fallback_remains_opt_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "caption_prose_opt_in.pdf"
    _build_caption_plus_prose_pdf(pdf_path)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("TABLE_TEXT_FALLBACK_ENABLED", "true")

    payload = extract_and_store_paper_tables(pdf_path, paper_id=90, blocks=[])

    assert payload["num_tables"] == 1
    assert payload["tables"][0]["detection_strategy"] == "text_caption_fallback"


class _FakeHeader:
    def __init__(self, names):
        self.names = names


class _FakeTable:
    def __init__(self, header_names):
        self.header = _FakeHeader(header_names)


class _FakeExtractTable:
    def __init__(self, bbox, rows):
        self.bbox = bbox
        self._rows = rows
        self.header = _FakeHeader(rows[0] if rows else [])

    def extract(self):
        return self._rows


class _FakeFinder:
    def __init__(self, tables):
        self.tables = tables


class _FakeRect:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1


class _FakeCaptionGuidedPage:
    def __init__(self, *, text_blocks, lines_tables=None, text_tables=None, width=595.0, height=842.0, find_tables_fn=None):
        self.rect = _FakeRect(0.0, 0.0, width, height)
        self._text_blocks = text_blocks
        self._lines_tables = list(lines_tables or [])
        self._text_tables = list(text_tables or [])
        self._find_tables_fn = find_tables_fn

    def get_text(self, mode):
        assert mode == "dict"
        return {"blocks": self._text_blocks}

    def find_tables(self, *, strategy, clip=None):
        if self._find_tables_fn is not None:
            tables = self._find_tables_fn(strategy=strategy, clip=clip)
            return _FakeFinder(tables)
        if strategy == "lines":
            return _FakeFinder(self._lines_tables)
        if strategy == "text":
            return _FakeFinder(self._text_tables)
        return _FakeFinder([])


def test_pick_headers_and_rows_merges_units_and_continuation_columns() -> None:
    matrix = [
        ["Method", "", "Match", "RMSD", "Valid", "Unique"],
        ["", "", "(%)", "(A ˚)", "(%)", "(%)"],
        ["EDM (Hoogeb", "oom et al., 2022)", "–", "–", "91.9", "90.7"],
        ["GeoLDM (Xu", "et al., 2023)", "–", "–", "93.8", "92.9"],
    ]
    headers, rows = _pick_headers_and_rows(matrix, _FakeTable(["Method", "", "Match", "RMSD", "Valid", "Unique"]))

    assert headers == ["Method", "Match (%)", "RMSD (A ˚)", "Valid (%)", "Unique (%)"]
    assert rows[0][0] == "EDM (Hoogeb oom et al., 2022)"
    assert rows[1][0] == "GeoLDM (Xu et al., 2023)"


def test_pick_headers_and_rows_trims_fragmented_prose_tail() -> None:
    matrix = [
        ["Method", "", "Match", "RMSD", "Valid", "Unique"],
        ["", "", "(%)", "(A ˚)", "(%)", "(%)"],
        ["EDM (Hoogeb", "oom et al., 2022)", "–", "–", "91.9", "90.7"],
        ["UNITE-S (Ou", "rs)", "99.37", "0.039", "94.90", "99.71"],
        ["pensive to", "obtain—less straig", "htforw", "ard, es", "pecial", "ly in"],
    ]

    headers, rows = _pick_headers_and_rows(matrix, _FakeTable(["Method", "", "Match", "RMSD", "Valid", "Unique"]))

    assert headers == ["Method", "Match (%)", "RMSD (A ˚)", "Valid (%)", "Unique (%)"]
    assert len(rows) == 2
    assert rows[-1][0] == "UNITE-S (Ou rs)"


def test_false_positive_table_detects_caption_leak_and_collapsed_single_column() -> None:
    matrix = [
        ["w/o TTVA"],
        ["+forward"],
        ["1m"],
        ["Table 6. Ablation results on SemanticKitti."],
    ]

    is_false_positive, reasons = _looks_like_false_positive_table(
        matrix,
        n_cols=1,
        row_count=4,
        table_caption="Table 6. Ablation results on SemanticKitti.",
        figure_caption=None,
    )

    assert is_false_positive is True
    assert "collapsed_single_column" in reasons


def test_missing_explicit_table_caption_indices_finds_unresolved_captions() -> None:
    caption_blocks = [
        {"text": "Table 1. Sequence setting."},
        {"text": "Table 2. Monocular setting."},
        {"text": "Not a table caption"},
    ]
    table_records = [
        {"page_no": 7, "caption": "Table 1. Sequence setting."},
        {"page_no": 8, "caption": "Table 2. Other page."},
    ]

    missing = _missing_explicit_table_caption_indices(caption_blocks, table_records, page_no=7)

    assert missing == {1}


def test_find_nearest_caption_block_prefers_horizontal_alignment_for_side_by_side_tables() -> None:
    caption_blocks = [
        {
            "text": "Table 1. Left table.",
            "bbox": {"x0": 58.0, "y0": 508.0, "x1": 296.0, "y1": 528.0},
        },
        {
            "text": "Table 2. Right table.",
            "bbox": {"x0": 317.0, "y0": 573.0, "x1": 554.0, "y1": 604.0},
        },
    ]
    target_bbox = {"x0": 328.0, "y0": 391.0, "x1": 539.0, "y1": 550.0}

    idx, block = _find_nearest_caption_block(caption_blocks, target_bbox)

    assert idx == 1
    assert block is not None
    assert block["text"] == "Table 2. Right table."


def test_resolve_candidate_caption_binding_rebinds_misaligned_text_fallback_candidate() -> None:
    caption_blocks = [
        {
            "text": "Table 5. Dataset statistics.",
            "bbox": {"x0": 70.0, "y0": 223.0, "x1": 525.0, "y1": 245.0},
        },
        {
            "text": "Table 6. Hyperparameters.",
            "bbox": {"x0": 305.0, "y0": 590.0, "x1": 524.0, "y1": 613.0},
        },
    ]
    candidate_bbox = {"x0": 312.0, "y0": 336.0, "x1": 525.0, "y1": 576.0}

    seed_score = _caption_block_match_score(caption_blocks[0]["bbox"], candidate_bbox)
    nearest_score = _caption_block_match_score(caption_blocks[1]["bbox"], candidate_bbox)

    assert nearest_score < seed_score

    idx, block = _resolve_candidate_caption_binding(
        caption_blocks=caption_blocks,
        candidate_bbox=candidate_bbox,
        detection_strategy="text_caption_fallback",
        seed_caption_index=0,
    )

    assert idx == 1
    assert block is caption_blocks[1]


def test_looks_like_explicit_table_caption_rejects_prose_mentions() -> None:
    assert _looks_like_explicit_table_caption("Table 6. Hyperparameter settings.") is True
    assert _looks_like_explicit_table_caption("Table 3 shows the write-back construction process.") is False


def test_materialize_table_record_rebinds_caption_after_reconstruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caption_blocks = [
        {
            "text": "Table 5. Dataset statistics.",
            "bbox": {"x0": 70.0, "y0": 223.0, "x1": 525.0, "y1": 245.0},
        },
        {
            "text": "Table 6. Hyperparameters.",
            "bbox": {"x0": 305.0, "y0": 590.0, "x1": 524.0, "y1": 613.0},
        },
    ]
    candidate = {
        "bbox": {"x0": 70.0, "y0": 90.0, "x1": 525.0, "y1": 208.0},
        "matrix": [["A", "B"], ["1", "2"]],
        "table_obj": None,
        "detection_strategy": "pymupdf_native",
    }
    reconstructed = {
        "bbox": {"x0": 312.0, "y0": 336.0, "x1": 525.0, "y1": 576.0},
        "matrix": [["Hyperparameter", "Value"], ["Retriever", "E5-base-v2"]],
        "table_obj": None,
        "detection_strategy": "pymupdf_text_reconstructed",
    }

    monkeypatch.setattr("ia_phase1.tables._candidate_needs_text_reconstruction", lambda **kwargs: True)
    monkeypatch.setattr("ia_phase1.tables._reconstruct_candidate_from_text", lambda *args, **kwargs: reconstructed)
    monkeypatch.setattr("ia_phase1.tables._repair_headers_from_auxiliary_band", lambda headers, rows, **kwargs: (headers, rows))
    monkeypatch.setattr("ia_phase1.tables._looks_like_false_positive_table", lambda *args, **kwargs: (False, []))
    monkeypatch.setattr(
        "ia_phase1.tables._infer_section_for_table",
        lambda *args, **kwargs: {
            "section_canonical": "other",
            "section_title": "Document Body",
            "section_source": "fallback",
            "section_confidence": 0.0,
        },
    )
    monkeypatch.setattr("ia_phase1.tables._render_table_markdown", lambda *args, **kwargs: "markdown")
    monkeypatch.setattr("ia_phase1.tables._to_csv_text", lambda *args, **kwargs: "csv")

    record = _materialize_table_record(
        page=None,
        page_no=12,
        paper_id=118,
        candidate=candidate,
        page_kept_bboxes=[],
        table_caption_blocks=caption_blocks,
        figure_caption_blocks=[],
        auxiliary_header_candidates=[],
        page_bounds={"x0": 0.0, "y0": 0.0, "x1": 595.0, "y1": 842.0},
        page_blocks_for_page=[],
        min_area=0.0,
        min_cols=2,
        min_rows=1,
        dedup_iou_threshold=0.9,
    )

    assert record is not None
    assert record["caption"] == "Table 6. Hyperparameters."


def test_repair_headers_from_auxiliary_band_expands_split_header_rows() -> None:
    headers = ["", "Speedup vs. PEFT", "DoRA", "Speedu", "p vs. E", "ager"]
    rows = [
        ["Model", "RTX H200", "B200", "RTX", "H200", "B200"],
        ["Qwen3.5-27B", "1.51× 1.57×", "1.57×", "1.22×", "1.21×", "1.23×"],
    ]
    auxiliary_candidates = [
        {
            "bbox": {"x0": 100.0, "y0": 80.0, "x1": 500.0, "y1": 110.0},
            "matrix": [
                ["", "Speedup vs. PEFT DoRA", "", "", "Speedup vs. Eager", "", ""],
                ["Model", "RTX", "H200", "B200", "RTX", "H200", "B200"],
            ],
            "raw_row_count": 2,
        }
    ]

    repaired_headers, repaired_rows = _repair_headers_from_auxiliary_band(
        headers,
        rows,
        candidate_bbox={"x0": 100.0, "y0": 118.0, "x1": 500.0, "y1": 220.0},
        auxiliary_header_candidates=auxiliary_candidates,
    )

    assert repaired_headers == [
        "Model",
        "Speedup vs. PEFT DoRA RTX",
        "Speedup vs. PEFT DoRA H200",
        "Speedup vs. PEFT DoRA B200",
        "Speedup vs. Eager RTX",
        "Speedup vs. Eager H200",
        "Speedup vs. Eager B200",
    ]
    assert repaired_rows == [["Qwen3.5-27B", "1.51×", "1.57×", "1.57×", "1.22×", "1.21×", "1.23×"]]


def test_repair_leading_text_fragment_columns_merges_split_method_prefix() -> None:
    headers = ["", "", "", "", "RULER-MV", "RULER", "-VT", "RULER-CWE", "BABIL", "ong"]
    rows = [
        ["Me", "thod", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "16K 32K", "16K", "32K", "16K 32K", "16K", "32K"],
        ["Sta", "ndard MDLM", "", "", "22.35 14.30", "52.56", "9.48", "44.20 17.82", "19.20", "6.8 0"],
        ["Me", "mDLM (Train-On", "ly)", "", "25.48 15.20", "55.30", "10.35", "54.25 22.48", "21.00", "8.5 0"],
    ]

    repaired_headers, repaired_rows = _repair_leading_text_fragment_columns(headers, rows)

    assert repaired_rows[0][0] == "Method"
    assert repaired_rows[2][0] == "Standard MDLM"
    assert repaired_rows[3][0] == "MemDLM (Train-Only)"


def test_repair_leading_text_fragment_columns_does_not_absorb_next_header_prefix() -> None:
    headers = ["M", "ethod", "T", "riviaQA", "PR-en"]
    rows = [
        ["S", "tandard MDLM", "", "55.29", "50.32"],
        ["M", "emDLM (Trai", "n-Only)", "87.74", "54.36"],
        ["M", "emDLM (Trai", "n & Inference)", "87.77", "54.69"],
    ]

    repaired_headers, repaired_rows = _repair_leading_text_fragment_columns(headers, rows)

    assert repaired_headers[0] == "Method"
    assert repaired_headers[1] == "T"
    assert repaired_rows[0][0] == "Standard MDLM"


def test_merge_sparse_pre_numeric_text_columns_merges_method_continuations_and_repairs_next_header() -> None:
    headers = ["Method", "T", "riviaQA", "PR-en"]
    rows = [
        ["Standard MDLM", "", "55.29", "50.32"],
        ["MemDLM (Trai", "n-Only)", "87.74", "54.36"],
        ["MemDLM (Trai", "n & Inference)", "87.77", "54.69"],
    ]

    repaired_headers, repaired_rows = _merge_sparse_pre_numeric_text_columns(headers, rows)

    assert repaired_headers == ["Method", "TriviaQA", "PR-en"]
    assert repaired_rows[0][0] == "Standard MDLM"
    assert repaired_rows[1][0] == "MemDLM (Train-Only)"
    assert repaired_rows[2][0] == "MemDLM (Train & Inference)"


def test_pick_headers_and_rows_trims_chart_scaffold_tail_after_real_data_rows() -> None:
    matrix = [
        ["Method", "TriviaQA", "PR-en", "PR-zh"],
        ["Standard MDLM", "55.29", "50.32", "74.50"],
        ["MemDLM (Train-Only)", "87.74", "54.36", "86.29"],
        ["MemDLM (Train & Inference)", "87.77", "54.69", "87.38"],
        ["", "", "Standard MDLM", ""],
        ["", "Train Loss", "", "Eval Loss"],
        ["", "1.8", "", "2.5"],
        ["", "Training step", "", "Training step"],
    ]

    headers, rows = _pick_headers_and_rows(matrix, _FakeTable(["Method", "TriviaQA", "PR-en", "PR-zh"]))

    assert headers == ["Method", "TriviaQA", "PR-en", "PR-zh"]
    assert len(rows) == 3
    assert rows[-1][0] == "MemDLM (Train & Inference)"


def test_false_positive_table_rejects_figure_like_shallow_grid_without_caption() -> None:
    matrix = [
        [
            "End-to-End Training for Unified To",
            "kenization and Latent Denoising Reconstruction 0.0 0.7 0.8 1.0 Noising Scale Figure 4. UNITE’s Training dynamics",
        ],
        [
            "3.2 End-to-End Training for UNITE",
            "",
        ],
    ]
    is_false_positive, reasons = _looks_like_false_positive_table(
        matrix,
        n_cols=2,
        row_count=1,
        table_caption=None,
        figure_caption=None,
    )

    assert is_false_positive is True
    assert "figure_like_content" in reasons or "shallow_without_table_caption" in reasons


def test_false_positive_table_rejects_when_figure_caption_is_much_closer_than_table_caption() -> None:
    matrix = [
        ["0", "H200"],
        ["", "B200"],
        ["", "2%"],
        ["", "Qwen3.5-27B"],
    ]
    is_false_positive, reasons = _looks_like_false_positive_table(
        matrix,
        n_cols=2,
        row_count=4,
        table_caption="Table 6: Speedup results.",
        figure_caption="Figure 5: Dense (B@A) position.",
        table_caption_gap=170.0,
        figure_caption_gap=24.0,
    )

    assert is_false_positive is True
    assert "figure_caption_closer_than_table_caption" in reasons


def test_append_or_replace_table_record_prefers_better_same_caption_same_page() -> None:
    records = [
        {
            "page_no": 15,
            "caption": "Table 8: Model-level peak VRAM (GB).",
            "headers": ["col_1", "col_2", "col_3"],
            "rows": [["", "", ""], ["", "", ""]],
            "detection_strategy": "pymupdf_lines_strict",
        }
    ]
    improved = {
        "page_no": 15,
        "caption": "Table 8: Model-level peak VRAM (GB).",
        "headers": ["Model", "RTX", "H200", "B200"],
        "rows": [["Qwen", "10", "8", "7"], ["Gemma", "11", "9", "8"]],
        "detection_strategy": "pymupdf_text_reconstructed",
    }

    _append_or_replace_table_record(records, improved)

    assert len(records) == 1
    assert records[0]["headers"] == ["Model", "RTX", "H200", "B200"]
