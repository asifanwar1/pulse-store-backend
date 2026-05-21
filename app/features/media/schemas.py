from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    id: str
    url: str


class MediaUploadResponse(MediaItem):
    bucket: str
    path: str


class MediaUploadRequest(BaseModel):
    folder: str = Field(default="general", min_length=1, max_length=100)
