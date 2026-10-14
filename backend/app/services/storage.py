"""
storage.py — Abstract storage backend for machine photos.

Two implementations ship by default:
  - LocalStorageBackend  (dev) — saves to /backend/media/machines/{machine_id}/
  - S3StorageBackend     (prod) — uploads to any S3-compatible bucket

Switch via env var:  STORAGE_BACKEND=local | s3
For S3 also set:    S3_BUCKET, S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
                    S3_ENDPOINT_URL (for MinIO / R2 etc.)

The URL returned by save() is always a fully-qualified public URL the client
can embed in an <img> tag.  Local URLs use the backend's own origin
(BACKEND_PUBLIC_URL env var, defaults to http://localhost:8000).
"""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings


class StorageBackend(ABC):
    """Swap-friendly interface. One method: save(file_bytes, filename, machine_id) -> public_url."""

    @abstractmethod
    async def save(self, file_bytes: bytes, original_filename: str, machine_id: int) -> str:
        ...


class LocalStorageBackend(StorageBackend):
    """Stores files on the local filesystem under <repo>/backend/media/machines/<id>/."""

    def __init__(self) -> None:
        # Resolve absolute path regardless of cwd
        self.base_dir = Path(__file__).resolve().parents[2] / "media" / "machines"

    async def save(self, file_bytes: bytes, original_filename: str, machine_id: int) -> str:
        ext = Path(original_filename).suffix.lower() or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_dir = self.base_dir / str(machine_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / unique_name
        dest.write_bytes(file_bytes)
        public_base = getattr(settings, "BACKEND_PUBLIC_URL", "http://localhost:8000")
        return f"{public_base.rstrip('/')}/media/machines/{machine_id}/{unique_name}"


class S3StorageBackend(StorageBackend):
    """Uploads to S3-compatible storage. Requires aioboto3 (`pip install aioboto3`)."""

    def __init__(self) -> None:
        self.bucket: str = os.environ["S3_BUCKET"]
        self.region: Optional[str] = os.environ.get("S3_REGION", "us-east-1")
        self.endpoint_url: Optional[str] = os.environ.get("S3_ENDPOINT_URL")  # MinIO / R2 / etc.
        self.public_base: str = os.environ.get(
            "S3_PUBLIC_BASE",
            f"https://{self.bucket}.s3.{self.region}.amazonaws.com",
        )

    async def save(self, file_bytes: bytes, original_filename: str, machine_id: int) -> str:
        try:
            import aioboto3  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "aioboto3 is required for S3 storage. Add it to requirements.txt."
            ) from exc

        ext = Path(original_filename).suffix.lower() or ".jpg"
        key = f"machines/{machine_id}/{uuid.uuid4().hex}{ext}"

        session = aioboto3.Session()
        async with session.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_bytes,
                ContentType="image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png",
            )
        return f"{self.public_base.rstrip('/')}/{key}"


def get_storage_backend() -> StorageBackend:
    """Factory — read STORAGE_BACKEND env var and return the right implementation."""
    backend_name = os.environ.get("STORAGE_BACKEND", "local").strip().lower()
    if backend_name == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()
