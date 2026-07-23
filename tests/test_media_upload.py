import io

import pytest
from PIL import Image

from app.core.exceptions import BadRequestException
from app.features.media import service as media_service
from app.features.users.models import UserType


class _FakeBucket:
    def __init__(self):
        self.uploaded = []

    def upload(self, path, file, file_options=None):
        self.uploaded.append((path, len(file)))

    def get_public_url(self, path):
        return f"https://fake.storage/{path}"


class _FakeStorage:
    def __init__(self, bucket):
        self._bucket = bucket

    def from_(self, bucket_name):
        return self._bucket


class _FakeSupabaseClient:
    def __init__(self, bucket):
        self.storage = _FakeStorage(bucket)


def _fake_get_supabase_client(monkeypatch):
    bucket = _FakeBucket()
    monkeypatch.setattr(media_service, "_get_supabase_client", lambda: _FakeSupabaseClient(bucket))
    return bucket


def _tiny_png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_read_limited_rejects_oversized_upload(tmp_path):
    class _FakeUploadFile:
        def __init__(self, data: bytes):
            self.file = io.BytesIO(data)

    oversized = _FakeUploadFile(b"0" * (media_service.MAX_UPLOAD_BYTES + 1))
    with pytest.raises(BadRequestException):
        media_service._read_limited(oversized, media_service.MAX_UPLOAD_BYTES)


def test_upload_endpoint_rejects_oversized_file(client, make_user, auth_headers, monkeypatch):
    bucket = _fake_get_supabase_client(monkeypatch)
    admin = make_user("media-admin-1@example.com", user_type=UserType.ADMIN.value)

    oversized_bytes = b"0" * (media_service.MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/api/v1/media/upload",
        files={"file": ("huge.png", oversized_bytes, "image/png")},
        headers=auth_headers(admin),
    )
    assert response.status_code == 400
    assert "limit" in response.json()["detail"].lower()
    assert bucket.uploaded == []


def test_upload_endpoint_accepts_valid_image_under_limit(client, make_user, auth_headers, monkeypatch):
    bucket = _fake_get_supabase_client(monkeypatch)
    admin = make_user("media-admin-2@example.com", user_type=UserType.ADMIN.value)

    response = client.post(
        "/api/v1/media/upload",
        files={"file": ("tiny.png", _tiny_png_bytes(), "image/png")},
        data={"folder": "products"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 201
    assert len(bucket.uploaded) == 1
    assert response.json()["url"].startswith("https://fake.storage/products/")


def test_upload_endpoint_requires_admin(client, make_user, auth_headers, monkeypatch):
    _fake_get_supabase_client(monkeypatch)
    non_admin = make_user("media-nonadmin@example.com")

    response = client.post(
        "/api/v1/media/upload",
        files={"file": ("tiny.png", _tiny_png_bytes(), "image/png")},
        headers=auth_headers(non_admin),
    )
    assert response.status_code == 403
