from __future__ import annotations

from pathlib import Path

from backend.core import database, storage


class _FakePutResult:
    etag = "fake-etag"
    version_id = "v1"


class _FakeObjectResponse:
    def __init__(self, data: bytes):
        self._data = data
        self.closed = False
        self.released = False

    def stream(self, chunk_size: int):
        for idx in range(0, len(self._data), chunk_size):
            yield self._data[idx : idx + chunk_size]

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class _FakeMinioClient:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(self, bucket: str, object_key: str, data, length: int, content_type: str):
        self.objects[(bucket, object_key)] = data.read(length)
        return _FakePutResult()

    def get_object(self, bucket: str, object_key: str, version_id: str | None = None):
        return _FakeObjectResponse(self.objects[(bucket, object_key)])

    def remove_object(self, bucket: str, object_key: str, version_id: str | None = None) -> None:
        self.objects.pop((bucket, object_key), None)


def _configure_temp_db(tmp_path: Path, monkeypatch) -> Path:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()
    return db_path


def _configure_minio(monkeypatch, client: _FakeMinioClient) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET_LIBRARY", "library-docs")
    monkeypatch.setenv("MINIO_SECURE", "false")
    monkeypatch.setattr(storage, "_MINIO_CLIENT", client)


def test_upload_primary_pdf_asset_inserts_asset_row(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)
    client = _FakeMinioClient()
    _configure_minio(monkeypatch, client)

    pdf_path = tmp_path / "paper.pdf"
    pdf_bytes = b"%PDF-1.4 fake pdf bytes"
    pdf_path.write_bytes(pdf_bytes)

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Test Paper", "https://example.test/paper", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    asset = storage.upload_primary_pdf_asset(
        paper_id,
        pdf_path,
        source_kind="local_pdf",
        original_filename="test-paper.pdf",
    )

    assert asset is not None
    assert asset["paper_id"] == paper_id
    assert asset["bucket"] == "library-docs"
    assert (asset["bucket"], asset["object_key"]) in client.objects
    assert client.objects[(asset["bucket"], asset["object_key"])] == pdf_bytes

    with database.get_conn() as conn:
        rows = conn.execute("SELECT * FROM paper_assets WHERE paper_id = ?", (paper_id,)).fetchall()
    assert len(rows) == 1
    assert int(rows[0]["is_primary"]) == 1
    assert storage.paper_ids_with_primary_pdf_assets([paper_id]) == {paper_id}


def test_open_and_delete_primary_pdf_asset(tmp_path: Path, monkeypatch) -> None:
    _configure_temp_db(tmp_path, monkeypatch)
    client = _FakeMinioClient()
    _configure_minio(monkeypatch, client)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 more fake pdf bytes")

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Stored Paper", "https://example.test/stored", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    asset = storage.upload_primary_pdf_asset(
        paper_id,
        pdf_path,
        source_kind="local_pdf",
        original_filename="stored-paper.pdf",
    )
    assert asset is not None

    found_asset, response = storage.open_primary_pdf_stream(paper_id)
    assert found_asset is not None
    streamed = b"".join(response.stream(8))
    assert streamed.startswith(b"%PDF-1.4")

    storage.delete_paper_assets(paper_id)
    assert client.objects == {}


def test_materialize_primary_pdf_path_downloads_from_object_storage_when_local_missing(
    tmp_path: Path, monkeypatch
) -> None:
    _configure_temp_db(tmp_path, monkeypatch)
    client = _FakeMinioClient()
    _configure_minio(monkeypatch, client)

    pdf_path = tmp_path / "paper.pdf"
    pdf_bytes = b"%PDF-1.4 object-backed bytes"
    pdf_path.write_bytes(pdf_bytes)

    with database.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO papers(title, source_url, pdf_path) VALUES(?,?,?)",
            ("Recovered Paper", "https://example.test/recovered", str(pdf_path)),
        )
        paper_id = int(cursor.lastrowid)
        conn.commit()

    asset = storage.upload_primary_pdf_asset(
        paper_id,
        pdf_path,
        source_kind="local_pdf",
        original_filename="recovered-paper.pdf",
    )
    assert asset is not None

    pdf_path.unlink()

    with storage.materialize_primary_pdf_path(paper_id, str(pdf_path)) as materialized:
        assert materialized.exists()
        assert materialized.read_bytes() == pdf_bytes

    assert not materialized.exists()
