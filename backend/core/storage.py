from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Set, Tuple

from .database import DATA_DIR, get_conn

logger = logging.getLogger(__name__)

_SAFE_KEY_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MINIO_CLIENT: Any = None


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def object_storage_enabled() -> bool:
    return bool(os.getenv("MINIO_ENDPOINT") and os.getenv("MINIO_BUCKET_LIBRARY"))


def _storage_backend_name() -> str:
    return os.getenv("MINIO_BACKEND_NAME", "minio")


def _sanitize_filename(name: str) -> str:
    stem = Path(name).name or "document.pdf"
    cleaned = _SAFE_KEY_RE.sub("_", stem).strip("._")
    return cleaned or "document.pdf"


def _paper_pdf_object_key(paper_id: int, filename: str) -> str:
    return f"papers/{paper_id}/primary/{_sanitize_filename(filename)}"


def _paper_asset_object_key(paper_id: int, role: str, filename: str) -> str:
    safe_role = _SAFE_KEY_RE.sub("_", str(role or "asset")).strip("._") or "asset"
    return f"papers/{paper_id}/{safe_role}/{_sanitize_filename(filename)}"


def _resolve_existing_local_pdf_path(raw_pdf_path: str | Path | None) -> Optional[Path]:
    if not raw_pdf_path:
        return None
    candidate = Path(raw_pdf_path).expanduser()
    if candidate.exists():
        return candidate.resolve()
    fallback = DATA_DIR / "pdfs" / candidate.name
    if fallback.exists():
        return fallback.resolve()
    return None


def resolve_local_pdf_path(raw_pdf_path: str | Path | None) -> Optional[Path]:
    return _resolve_existing_local_pdf_path(raw_pdf_path)


def _sha256_and_size(path: Path) -> Tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _minio_bucket_name() -> str:
    bucket = os.getenv("MINIO_BUCKET_LIBRARY", "").strip()
    if not bucket:
        raise RuntimeError("MINIO_BUCKET_LIBRARY is not configured.")
    return bucket


def _ensure_bucket(client: Any, bucket: str) -> None:
    if client.bucket_exists(bucket):
        return
    if not _truthy_env("MINIO_AUTO_CREATE_BUCKET", default=True):
        raise RuntimeError(f"MinIO bucket does not exist: {bucket}")
    client.make_bucket(bucket)


def _get_minio_client() -> Any:
    global _MINIO_CLIENT
    if _MINIO_CLIENT is not None:
        return _MINIO_CLIENT
    if not object_storage_enabled():
        raise RuntimeError("Object storage is not configured.")
    from minio import Minio

    endpoint = os.getenv("MINIO_ENDPOINT", "").strip()
    access_key = os.getenv("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.getenv("MINIO_SECRET_KEY", "").strip()
    if not endpoint or not access_key or not secret_key:
        raise RuntimeError("MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY are required.")
    _MINIO_CLIENT = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=_truthy_env("MINIO_SECURE", default=False),
        region=os.getenv("MINIO_REGION") or None,
    )
    return _MINIO_CLIENT


def upload_primary_pdf_asset(
    paper_id: int,
    pdf_path: str | Path,
    *,
    source_kind: str,
    original_filename: Optional[str] = None,
    external_file_id: Optional[str] = None,
    external_revision: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    return upload_paper_asset(
        paper_id,
        pdf_path,
        role="primary_pdf",
        source_kind=source_kind,
        original_filename=original_filename,
        external_file_id=external_file_id,
        external_revision=external_revision,
        mime_type="application/pdf",
        is_primary=True,
    )


def upload_paper_asset(
    paper_id: int,
    file_path: str | Path,
    *,
    role: str,
    source_kind: str,
    original_filename: Optional[str] = None,
    external_file_id: Optional[str] = None,
    external_revision: Optional[str] = None,
    mime_type: Optional[str] = None,
    is_primary: bool = False,
) -> Optional[Dict[str, Any]]:
    if not object_storage_enabled():
        return None

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Asset file not found at {path}")

    filename = original_filename or path.name
    if role == "primary_pdf":
        object_key = _paper_pdf_object_key(paper_id, filename)
    else:
        object_key = _paper_asset_object_key(paper_id, role, filename)
    sha256, size_bytes = _sha256_and_size(path)
    resolved_mime_type = mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    bucket = _minio_bucket_name()
    client = _get_minio_client()
    _ensure_bucket(client, bucket)

    with path.open("rb") as handle:
        result = client.put_object(
            bucket,
            object_key,
            handle,
            length=size_bytes,
            content_type=resolved_mime_type,
        )

    with get_conn() as conn:
        if is_primary:
            conn.execute(
                """
                UPDATE paper_assets
                SET is_primary = 0, updated_at = datetime('now')
                WHERE paper_id = ? AND role = ? AND is_primary = 1
                """,
                (paper_id, role),
            )
        cursor = conn.execute(
            """
            INSERT INTO paper_assets(
              paper_id, role, storage_backend, bucket, object_key, version_id,
              mime_type, size_bytes, sha256, etag, original_filename,
              source_kind, external_file_id, external_revision, is_primary
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paper_id,
                role,
                _storage_backend_name(),
                bucket,
                object_key,
                getattr(result, "version_id", None),
                resolved_mime_type,
                size_bytes,
                sha256,
                getattr(result, "etag", None),
                filename,
                source_kind,
                external_file_id,
                external_revision,
                1 if is_primary else 0,
            ),
        )
        asset_id = int(cursor.lastrowid)
        conn.commit()

    return {
        "id": asset_id,
        "paper_id": paper_id,
        "storage_backend": _storage_backend_name(),
        "bucket": bucket,
        "object_key": object_key,
        "mime_type": resolved_mime_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "etag": getattr(result, "etag", None),
        "version_id": getattr(result, "version_id", None),
        "original_filename": filename,
        "source_kind": source_kind,
        "external_file_id": external_file_id,
        "external_revision": external_revision,
        "is_primary": 1 if is_primary else 0,
    }


def get_primary_pdf_asset(paper_id: int) -> Optional[Dict[str, Any]]:
    return get_paper_asset(paper_id, role="primary_pdf")


def get_paper_asset(
    paper_id: int,
    *,
    role: str,
    original_filename: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        with get_conn() as conn:
            if original_filename:
                row = conn.execute(
                    """
                    SELECT *
                    FROM paper_assets
                    WHERE paper_id = ? AND role = ? AND original_filename = ?
                    ORDER BY is_primary DESC, datetime(updated_at) DESC, id DESC
                    LIMIT 1
                    """,
                    (paper_id, role, original_filename),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT *
                    FROM paper_assets
                    WHERE paper_id = ? AND role = ?
                    ORDER BY is_primary DESC, datetime(updated_at) DESC, id DESC
                    LIMIT 1
                    """,
                    (paper_id, role),
                ).fetchone()
    except sqlite3.OperationalError:
        return None
    return dict(row) if row else None


def paper_ids_with_primary_pdf_assets(paper_ids: Optional[Iterable[int]] = None) -> Set[int]:
    query = "SELECT DISTINCT paper_id FROM paper_assets WHERE role='primary_pdf'"
    params: Tuple[Any, ...] = ()
    if paper_ids is not None:
        ids = [int(pid) for pid in paper_ids]
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        query += f" AND paper_id IN ({placeholders})"
        params = tuple(ids)
    try:
        with get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
    except sqlite3.OperationalError:
        return set()
    return {int(row["paper_id"]) for row in rows}


def open_primary_pdf_stream(paper_id: int) -> Tuple[Optional[Dict[str, Any]], Any]:
    asset = get_primary_pdf_asset(paper_id)
    return open_paper_asset_stream(asset)


def open_paper_asset_stream(asset: Optional[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Any]:
    if not asset or asset.get("storage_backend") != _storage_backend_name():
        return None, None
    client = _get_minio_client()
    response = client.get_object(
        asset["bucket"],
        asset["object_key"],
        version_id=asset.get("version_id") or None,
    )
    return asset, response


def load_json_paper_asset(
    paper_id: int,
    *,
    role: str,
    original_filename: str = "manifest.json",
) -> Optional[Dict[str, Any]]:
    asset = get_paper_asset(paper_id, role=role, original_filename=original_filename)
    asset, response = open_paper_asset_stream(asset)
    if asset is None or response is None:
        return None
    try:
        chunks = bytearray()
        for chunk in response.stream(1024 * 1024):
            chunks.extend(chunk)
        payload = json.loads(chunks.decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    finally:
        response.close()
        response.release_conn()


def restore_primary_pdf_to_path(paper_id: int, destination_path: str | Path) -> Path:
    asset, response = open_primary_pdf_stream(paper_id)
    if asset is None or response is None:
        raise FileNotFoundError(f"No object-stored PDF found for paper_id={paper_id}")

    destination = Path(destination_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_name(f".{destination.name}.tmp")
    try:
        with tmp_path.open("wb") as handle:
            for chunk in response.stream(1024 * 1024):
                handle.write(chunk)
        tmp_path.replace(destination)
        return destination.resolve()
    finally:
        try:
            response.close()
        finally:
            response.release_conn()
        tmp_path.unlink(missing_ok=True)


def object_asset_exists(asset: Optional[Dict[str, Any]]) -> Optional[bool]:
    if not asset:
        return None
    if asset.get("storage_backend") != _storage_backend_name():
        return None
    if not object_storage_enabled():
        return None

    client = _get_minio_client()
    try:
        client.stat_object(
            asset["bucket"],
            asset["object_key"],
            version_id=asset.get("version_id") or None,
        )
    except Exception as exc:
        code = getattr(exc, "code", None)
        message = str(exc)
        if code in {"NoSuchKey", "NoSuchObject", "NoSuchVersion", "NoSuchBucket"}:
            return False
        if any(token in message for token in ("NoSuchKey", "NoSuchObject", "NoSuchVersion", "NoSuchBucket")):
            return False
        raise
    return True


def primary_pdf_asset_exists_in_object_storage(paper_id: int) -> Optional[bool]:
    return object_asset_exists(get_primary_pdf_asset(paper_id))


@contextmanager
def materialize_primary_pdf_path(
    paper_id: int,
    raw_pdf_path: str | Path | None = None,
) -> Iterator[Path]:
    local_path = _resolve_existing_local_pdf_path(raw_pdf_path)
    if local_path is not None:
        yield local_path
        return

    asset, response = open_primary_pdf_stream(paper_id)
    if asset is None or response is None:
        raise FileNotFoundError(f"No local or object-stored PDF found for paper_id={paper_id}")

    suffix = Path(str(asset.get("original_filename") or f"paper-{paper_id}.pdf")).suffix or ".pdf"
    tmp_file = tempfile.NamedTemporaryFile(prefix=f"paper_{paper_id}_", suffix=suffix, delete=False)
    tmp_path = Path(tmp_file.name)
    try:
        with tmp_file:
            for chunk in response.stream(1024 * 1024):
                tmp_file.write(chunk)
        yield tmp_path
    finally:
        try:
            response.close()
        finally:
            response.release_conn()
        tmp_path.unlink(missing_ok=True)


def delete_paper_assets(paper_id: int) -> None:
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM paper_assets WHERE paper_id = ?", (paper_id,)).fetchall()
    except sqlite3.OperationalError:
        return
    if not rows:
        return

    if object_storage_enabled():
        try:
            client = _get_minio_client()
        except Exception as exc:
            logger.warning("Failed to initialize object storage client during delete for paper_id=%s: %s", paper_id, exc)
            return
        for row in rows:
            asset = dict(row)
            if asset.get("storage_backend") != _storage_backend_name():
                continue
            try:
                client.remove_object(
                    asset["bucket"],
                    asset["object_key"],
                    version_id=asset.get("version_id") or None,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to remove object-storage asset for paper_id=%s key=%s: %s",
                    paper_id,
                    asset.get("object_key"),
                    exc,
                )


def delete_paper_assets_by_role(paper_id: int, roles: Iterable[str]) -> int:
    wanted_roles = [str(role).strip() for role in roles if str(role).strip()]
    if not wanted_roles:
        return 0
    placeholders = ",".join("?" for _ in wanted_roles)
    params: Tuple[Any, ...] = (paper_id, *wanted_roles)
    try:
        with get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM paper_assets WHERE paper_id = ? AND role IN ({placeholders})",
                params,
            ).fetchall()
            if not rows:
                return 0
            conn.execute(
                f"DELETE FROM paper_assets WHERE paper_id = ? AND role IN ({placeholders})",
                params,
            )
            conn.commit()
    except sqlite3.OperationalError:
        return 0

    deleted = len(rows)
    if object_storage_enabled():
        try:
            client = _get_minio_client()
        except Exception as exc:
            logger.warning("Failed to initialize object storage client during role delete for paper_id=%s: %s", paper_id, exc)
            return deleted
        for row in rows:
            asset = dict(row)
            if asset.get("storage_backend") != _storage_backend_name():
                continue
            try:
                client.remove_object(
                    asset["bucket"],
                    asset["object_key"],
                    version_id=asset.get("version_id") or None,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to remove object-storage asset for paper_id=%s key=%s: %s",
                    paper_id,
                    asset.get("object_key"),
                    exc,
                )
    return deleted
