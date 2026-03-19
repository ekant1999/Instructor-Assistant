from __future__ import annotations

from pathlib import Path

from backend.core import database, library_tools
from backend.schemas import QuestionContextUploadResponse


def _configure_temp_db(tmp_path: Path, monkeypatch) -> Path:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()
    return db_path


def test_find_library_papers_and_excerpt_keyword_only(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "worldcam.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            (
                "WorldCam: Interactive Autoregressive 3D Gaming Worlds",
                "https://example.test/worldcam",
                str(pdf_path),
            ),
        )
        paper_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
            (paper_id, 1, "WorldCam uses camera pose as a unifying geometric representation."),
        )
        conn.execute(
            "INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)",
            (paper_id, 2, "Additional experiments and ablations."),
        )
        conn.commit()

    papers = library_tools.find_library_papers("WorldCam", limit=3, search_type="keyword")
    assert papers
    assert papers[0]["paper_id"] == paper_id
    assert papers[0]["pdf_reference"]["api_path"] == f"/api/papers/{paper_id}/file"

    monkeypatch.setattr(library_tools, "_keyword_match_lookup_for_sections", lambda *args, **kwargs: {})
    excerpt = library_tools.get_library_excerpt(
        paper_id,
        query="camera pose",
        search_type="keyword",
        max_chars=500,
        limit=3,
    )
    assert excerpt["excerpt"]["page_no"] == 1
    assert "camera pose" in excerpt["excerpt"]["text"].lower()


def test_get_library_pdf_reference_uses_local_pdf(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "agentfactory.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("AgentFactory", "https://example.test/agentfactory", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    payload = library_tools.get_library_pdf(paper_id)
    assert payload["delivery"] == "reference"
    assert payload["reference"]["api_path"] == f"/api/papers/{paper_id}/file"
    assert payload["filename"] == "agentfactory.pdf"


def test_list_library_figures_uses_manifest(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Figure Paper", "https://example.test/figure", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    monkeypatch.setattr(
        library_tools.paper_figures,
        "load_paper_figure_manifest",
        lambda pid: {
            "paper_id": pid,
            "images": [
                {
                    "id": 1,
                    "paper_id": pid,
                    "page_no": 3,
                    "file_name": "figure_001.png",
                    "section_canonical": "methodology",
                    "section_title": "Methodology",
                    "figure_type": "embedded",
                    "figure_caption": "Pipeline overview",
                    "bbox": {"x0": 1, "y0": 2, "x1": 3, "y1": 4},
                }
            ],
        },
    )

    payload = library_tools.list_library_figures(paper_id, section_canonical="methodology")
    assert payload["figure_count"] == 1
    assert payload["figures"][0]["figure_name"] == "figure_001.png"
    assert payload["figures"][0]["image_reference"]["api_path"] == f"/api/papers/{paper_id}/figures/figure_001.png"


def test_get_library_section_uses_ingestion_rows_and_manifests(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Section Paper", "https://example.test/section", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    monkeypatch.setattr(
        library_tools,
        "_fetch_text_blocks",
        lambda pid: [
            {
                "id": 11,
                "page_no": 4,
                "block_index": 0,
                "text": "Method details go here.",
                "metadata": {
                    "section_primary": "methodology",
                    "section_all": ["methodology"],
                    "blocks": [
                        {
                            "page_no": 4,
                            "block_index": 0,
                            "text": "Method details go here.",
                            "bbox": {"x0": 10, "y0": 20, "x1": 30, "y1": 40},
                            "metadata": {
                                "section_canonical": "methodology",
                                "section_title": "Methodology",
                                "section_source": "pdf_toc",
                                "section_confidence": 0.9,
                            },
                        }
                    ],
                },
            }
        ],
    )
    monkeypatch.setattr(
        library_tools.paper_figures,
        "load_paper_figure_manifest",
        lambda pid: {
            "paper_id": pid,
            "images": [
                {
                    "id": 1,
                    "paper_id": pid,
                    "page_no": 4,
                    "file_name": "figure_001.png",
                    "section_canonical": "methodology",
                    "section_title": "Methodology",
                    "figure_caption": "Method figure",
                }
            ],
        },
    )
    monkeypatch.setattr(
        library_tools.equation_extractor,
        "load_paper_equation_manifest",
        lambda pid: {
            "paper_id": pid,
            "equations": [
                {
                    "id": 7,
                    "paper_id": pid,
                    "page_no": 4,
                    "equation_number": "1",
                    "text": "x = y + z",
                    "section_canonical": "methodology",
                    "section_title": "Methodology",
                    "file_name": "equation_0001.png",
                    "json_file": "equation_0001.json",
                }
            ],
        },
    )
    monkeypatch.setattr(
        library_tools.table_extractor,
        "load_paper_table_manifest",
        lambda pid: {
            "paper_id": pid,
            "tables": [
                {
                    "id": 3,
                    "paper_id": pid,
                    "page_no": 4,
                    "caption": "Method table",
                    "section_canonical": "methodology",
                    "section_title": "Methodology",
                    "n_rows": 3,
                    "n_cols": 2,
                    "json_file": "table_0001.json",
                }
            ],
        },
    )

    payload = library_tools.get_library_section(paper_id, "methodology", max_chars=1000)
    assert payload["section_canonical"] == "methodology"
    assert payload["pages"] == [4]
    assert "Method details" in payload["full_text"]
    assert payload["images"][0]["figure_name"] == "figure_001.png"
    assert payload["equations"][0]["equation_number"] == "1"
    assert payload["equations"][0]["image_reference"]["api_path"] == f"/api/papers/{paper_id}/equations/equation_0001.png"
    assert payload["tables"][0]["json_file"] == "table_0001.json"


def test_get_library_section_does_not_pull_front_matter_equation_by_page_fallback(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("WorldCam", "https://example.test/worldcam", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    monkeypatch.setattr(
        library_tools,
        "_fetch_text_blocks",
        lambda pid: [
            {
                "id": 11,
                "page_no": 1,
                "block_index": 0,
                "text": "Introduction text on page one.",
                "metadata": {
                    "section_primary": "introduction",
                    "section_all": ["introduction"],
                    "blocks": [
                        {
                            "page_no": 1,
                            "block_index": 0,
                            "text": "Introduction text on page one.",
                            "metadata": {
                                "section_canonical": "introduction",
                                "section_title": "Introduction",
                                "section_source": "pdf_toc",
                                "section_confidence": 0.9,
                            },
                        }
                    ],
                },
            },
            {
                "id": 12,
                "page_no": 2,
                "block_index": 0,
                "text": "More introduction text.",
                "metadata": {
                    "section_primary": "introduction",
                    "section_all": ["introduction"],
                    "blocks": [
                        {
                            "page_no": 2,
                            "block_index": 0,
                            "text": "More introduction text.",
                            "metadata": {
                                "section_canonical": "introduction",
                                "section_title": "Introduction",
                                "section_source": "pdf_toc",
                                "section_confidence": 0.9,
                            },
                        }
                    ],
                },
            },
        ],
    )
    monkeypatch.setattr(
        library_tools.paper_figures,
        "load_paper_figure_manifest",
        lambda pid: {"paper_id": pid, "images": []},
    )
    monkeypatch.setattr(
        library_tools.equation_extractor,
        "load_paper_equation_manifest",
        lambda pid: {
            "paper_id": pid,
            "equations": [
                {
                    "id": 1,
                    "page_no": 1,
                    "section_canonical": "front_matter",
                    "section_title": "Front Matter",
                    "text": "Date: 2026.03.17",
                    "file_name": "equation_0001.png",
                    "json_file": "equation_0001.json",
                    "url": f"/api/papers/{pid}/equations/equation_0001.png",
                }
            ],
        },
    )
    monkeypatch.setattr(
        library_tools.table_extractor,
        "load_paper_table_manifest",
        lambda pid: {"paper_id": pid, "tables": []},
    )

    payload = library_tools.get_library_section(paper_id, "introduction", max_chars=1000)
    assert payload["pages"] == [1, 2]
    assert payload["equations"] == []


def test_load_library_paper_context_from_full_paper(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Context Paper", "https://example.test/context", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.execute("INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)", (paper_id, 1, "First page text."))
        conn.execute("INSERT INTO sections(paper_id, page_no, text) VALUES(?,?,?)", (paper_id, 2, "Second page text."))
        conn.commit()

    ctx = library_tools.load_library_paper_context(paper_id, max_chars=1000)
    assert isinstance(ctx, QuestionContextUploadResponse)
    assert ctx.filename == "Context Paper"
    assert "First page text." in ctx.text
    assert "Second page text." in ctx.text
    assert ctx.characters == len(ctx.text)


def test_load_library_paper_context_from_section(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Section Context Paper", "https://example.test/section-context", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    monkeypatch.setattr(
        library_tools,
        "get_library_section",
        lambda pid, section_canonical, max_chars=60000: {
            "paper_id": pid,
            "section_canonical": section_canonical,
            "full_text": "Method section body.",
        },
    )

    ctx = library_tools.load_library_paper_context(paper_id, section_canonical="methodology", max_chars=1000)
    assert isinstance(ctx, QuestionContextUploadResponse)
    assert ctx.filename == "Section Context Paper [methodology]"
    assert ctx.text == "Method section body."
