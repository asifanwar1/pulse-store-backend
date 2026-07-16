import io
import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import BadRequestException
from app.features.media.schemas import MediaUploadResponse


ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}
OUTPUT_CONTENT_TYPE = "image/webp"
OUTPUT_QUALITY = 85  # visually lossless at this quality; ~60-80% smaller than source PNG
MAX_DIMENSION = 2000  # longest side, px — guards against oversized canvas exports

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


def _optimize_image(file_bytes: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Image.DecompressionBombError:
        raise BadRequestException("Image resolution is too large")
    except (UnidentifiedImageError, OSError, ValueError):
        raise BadRequestException("Uploaded file is not a valid image")

    # Sniff the real format instead of trusting the client's declared content-type.
    if image.format not in ALLOWED_IMAGE_FORMATS:
        raise BadRequestException("Only JPEG, PNG, and WEBP images are supported")

    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if has_alpha else "RGB")

    width, height = image.size
    if max(width, height) > MAX_DIMENSION:
        scale = MAX_DIMENSION / max(width, height)
        image = image.resize(
            (round(width * scale), round(height * scale)), Image.LANCZOS)

    # Re-encoding via Pillow (without passing exif=) drops any EXIF metadata as a side effect.
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=OUTPUT_QUALITY, method=6)
    return buffer.getvalue()


def upload_media(file: UploadFile, folder: str = "general") -> MediaUploadResponse:
    file_bytes = file.file.read()
    if not file_bytes:
        raise BadRequestException("Uploaded file is empty")

    optimized_bytes = _optimize_image(file_bytes)

    normalized_folder = _normalize_folder(folder)
    storage_path = f"{normalized_folder}/{uuid4().hex}.webp"

    bucket_name = settings.SUPABASE_STORAGE_BUCKET
    bucket = _get_supabase_client().storage.from_(bucket_name)
    bucket.upload(
        path=storage_path,
        file=optimized_bytes,
        file_options={
            "content-type": OUTPUT_CONTENT_TYPE,
            "upsert": "false",
        },
    )

    public_url = bucket.get_public_url(storage_path)
    return MediaUploadResponse(
        id=storage_path,
        url=public_url,
        file_name=Path(storage_path).name,
        bucket=bucket_name,
        path=storage_path,
    )
