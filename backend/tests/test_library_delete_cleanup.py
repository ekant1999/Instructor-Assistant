from __future__ import annotations

from pathlib import Path

from backend.core import database, library
from backend.tests.test_storage import _configure_temp_db


def test_delete_paper_removes_local_artifact_directories(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)
    monkeypatch.setenv("TABLE_OUTPUT_DIR", str(tmp_path / "tables"))
    monkeypatch.setenv("EQUATION_OUTPUT_DIR", str(tmp_path / "equations"))
    monkeypatch.setenv("FIGURE_OUTPUT_DIR", str(tmp_path / "figures"))
    monkeypatch.setenv("THUMBNAIL_OUTPUT_DIR", str(tmp_path / "thumbnails"))
    monkeypatch.setenv("MARKDOWN_OUTPUT_DIR", str(tmp_path / "markdown"))

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 cleanup test")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Cleanup Paper", "https://example.test/cleanup", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Other Paper", "https://example.test/other", str(pdf_path)),
        )
        other_paper_id = int(cursor.lastrowid)
        conn.commit()

    roots = [
        tmp_path / "tables",
        tmp_path / "equations",
        tmp_path / "figures",
        tmp_path / "thumbnails",
        tmp_path / "markdown",
    ]

    for root in roots:
        target_dir = root / str(paper_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "artifact.txt").write_text("cleanup", encoding="utf-8")

        sibling_dir = root / str(other_paper_id)
        sibling_dir.mkdir(parents=True, exist_ok=True)
        (sibling_dir / "artifact.txt").write_text("keep", encoding="utf-8")

    result = library.delete_paper(paper_id)

    assert result["deleted"] is True
    assert len(result["artifact_dirs_removed"]) == 5

    for root in roots:
        assert not (root / str(paper_id)).exists()
        assert (root / str(other_paper_id)).exists()

    with database.get_conn() as conn:
        deleted_row = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
        remaining_row = conn.execute("SELECT id FROM papers WHERE id = ?", (other_paper_id,)).fetchone()
    assert deleted_row is None
    assert remaining_row is not None
