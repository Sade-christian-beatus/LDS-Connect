"""Stockage de fichiers (photos, documents) : disque local par défaut, S3 compatible en option."""

from pathlib import Path, PurePosixPath
from typing import Protocol

from lds_api.core.config import get_settings


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


def _safe_key(key: str) -> PurePosixPath:
    p = PurePosixPath(key)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("Clé de fichier invalide")
    return p


class LocalStorage:
    """Fichiers sur le disque du serveur (volume Docker `storage`)."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        return self.root.joinpath(*_safe_key(key).parts)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    """Tout service compatible S3 (MinIO, Ceph, fournisseurs cloud). Nécessite `boto3`
    (dépendance optionnelle : `uv add boto3`) et les variables AWS_ACCESS_KEY_ID /
    AWS_SECRET_ACCESS_KEY."""

    def __init__(self, bucket: str, endpoint_url: str | None) -> None:
        try:
            import boto3  # noqa: PLC0415 — dépendance optionnelle
        except ImportError as exc:
            raise RuntimeError("STORAGE_BACKEND=s3 nécessite le paquet boto3") from exc
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=str(_safe_key(key)), Body=data, ContentType=content_type
        )

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=str(_safe_key(key)))["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=str(_safe_key(key)))


def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "s3":
        if not s.s3_bucket:
            raise RuntimeError("S3_BUCKET doit être défini")
        return S3Storage(s.s3_bucket, s.s3_endpoint_url)
    return LocalStorage(s.storage_local_path)
