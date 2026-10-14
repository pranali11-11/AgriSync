"""
POST /uploads/machine-photos

Accepts multipart/form-data with up to 5 photos (jpg/png, max 5 MB each).
Returns a list of public URLs.

The actual storage is handled by a swappable StorageBackend (see services/storage.py).
To switch from local disk to S3: set STORAGE_BACKEND=s3 in the environment.
"""
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models.machine import Machine
from app.models.user import User
from app.services.storage import get_storage_backend

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_PHOTOS = 5
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post(
    "/uploads/machine-photos",
    status_code=status.HTTP_200_OK,
    summary="Upload machine photos (max 5, jpg/png, 5 MB each)",
)
async def upload_machine_photos(
    machine_id: int = Form(..., description="The machine ID these photos belong to"),
    files: List[UploadFile] = File(..., description="Photo files (jpg/png, max 5 MB each)"),
    current_user: User = Depends(require_role("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > MAX_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can upload at most {MAX_PHOTOS} photos at once.",
        )

    machine = (
        await db.execute(select(Machine).where(Machine.id == machine_id))
    ).scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found.")
    if current_user.role != "admin" and machine.provider_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this machine listing.",
        )

    storage = get_storage_backend()
    urls: List[str] = []

    for upload in files:
        # Validate MIME type
        content_type = (upload.content_type or "").lower()
        extension = Path(upload.filename or "").suffix.lower()
        if content_type not in ALLOWED_MIME_TYPES or extension not in {".jpg", ".jpeg", ".png"}:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File '{upload.filename}' is not a supported image type. Only JPEG and PNG are accepted.",
            )

        # Read and validate size
        data = await upload.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{upload.filename}' exceeds the 5 MB size limit.",
            )

        is_jpeg = data.startswith(b"\xff\xd8\xff")
        is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
        if not (is_jpeg if content_type in {"image/jpeg", "image/jpg"} else is_png):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File '{upload.filename}' is not a valid JPEG or PNG image.",
            )

        try:
            url = await storage.save(data, upload.filename or "photo.jpg", machine_id)
        except Exception:
            logger.exception("Failed to save photo for machine %d", machine_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Photo upload failed. Please try again.",
            )

        urls.append(url)

    return {"urls": urls, "count": len(urls)}
