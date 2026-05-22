from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class MediaItem(BaseModel):
    id: str
    url: str
    file_name: str | None = None

    @model_validator(mode="after")
    def populate_file_name(self):
        if self.file_name:
            return self

        if self.id:
            self.file_name = Path(self.id).name
        elif self.url:
            self.file_name = Path(urlparse(self.url).path).name

        return self


class MediaUploadResponse(MediaItem):
    bucket: str
    path: str


class MediaUploadRequest(BaseModel):
    folder: str = Field(default="general", min_length=1, max_length=100)
