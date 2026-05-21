from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import BadRequestException


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_supabase_client: Client | None = None


def _get_supabase_client() -> Client:
    global _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise BadRequestException("Supabase storage is not configured")

    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    return _supabase_client


def upload_product_media(file: UploadFile) -> dict[str, str]:
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise BadRequestException("Only JPEG, PNG, and WEBP images are supported")

    file_extension = Path(file.filename or "").suffix.lower()
    if not file_extension:
        file_extension = ALLOWED_IMAGE_CONTENT_TYPES[file.content_type]

    storage_path = f"products/{uuid4().hex}{file_extension}"
    file_bytes = file.file.read()
    if not file_bytes:
        raise BadRequestException("Uploaded file is empty")

    bucket = _get_supabase_client().storage.from_(settings.SUPABASE_STORAGE_BUCKET)
    bucket.upload(
        path=storage_path,
        file=file_bytes,
        file_options={
            "content-type": file.content_type,
            "upsert": "false",
        },
    )

    public_url = bucket.get_public_url(storage_path)
    return {"id": storage_path, "url": public_url}
