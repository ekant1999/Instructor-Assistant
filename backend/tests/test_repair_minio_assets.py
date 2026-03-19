from __future__ import annotations

from pathlib import Path

from backend.core import database, storage
from backend.scripts import repair_minio_assets
from backend.tests.test_storage import _FakeMinioClient, _configure_minio, _configure_temp_db


def test_repair_paper_uploads_missing_primary_asset(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)
    client = _FakeMinioClient()
    _configure_minio(monkeypatch, client)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 repair me")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Repair Me", "https://example.test/repair", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    row = {
        "id": paper_id,
        "title": "Repair Me",
        "source_url": "https://example.test/repair",
        "pdf_path": str(pdf_path),
    }
    result = repair_minio_assets._repair_paper(
        row,
        repair_local_cache=False,
        dry_run=False,
    )

    assert result["errors"] == []
    assert len(result["actions"]) == 1
    assert result["actions"][0]["action"] == "upload_primary_asset"

    asset = storage.get_primary_pdf_asset(paper_id)
    assert asset is not None
    assert storage.object_asset_exists(asset) is True
