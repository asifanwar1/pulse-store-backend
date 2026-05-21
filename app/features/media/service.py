import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import BadRequestException
from app.features.media.schemas import MediaUploadResponse


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

_supabase_client: Client | None = None


def _get_supabase_client() -> Client:
    global _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise BadRequestException("Supabase storage is not configured")

    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    return _supabase_client


def _normalize_folder(folder: str) -> str:
    normalized = re.sub(r"[^a-z0-9/_-]+", "-",
                        folder.strip().lower()).strip("-/")
    if not normalized:
        raise BadRequestException("folder must contain letters or numbers")
    return normalized


def upload_media(file: UploadFile, folder: str = "general") -> MediaUploadResponse:
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise BadRequestException(
            "Only JPEG and PNG images are supported")

    file_extension = Path(file.filename or "").suffix.lower()
    if not file_extension:
        file_extension = ALLOWED_IMAGE_CONTENT_TYPES[file.content_type]

    file_bytes = file.file.read()
    if not file_bytes:
        raise BadRequestException("Uploaded file is empty")

    normalized_folder = _normalize_folder(folder)
    storage_path = f"{normalized_folder}/{uuid4().hex}{file_extension}"

    bucket_name = settings.SUPABASE_STORAGE_BUCKET
    bucket = _get_supabase_client().storage.from_(bucket_name)
    bucket.upload(
        path=storage_path,
        file=file_bytes,
        file_options={
            "content-type": file.content_type,
            "upsert": "false",
        },
    )

    public_url = bucket.get_public_url(storage_path)
    return MediaUploadResponse(
        id=storage_path,
        url=public_url,
        file_name=file.filename or Path(storage_path).name,
        bucket=bucket_name,
        path=storage_path,
    )
