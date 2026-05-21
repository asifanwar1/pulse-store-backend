from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.features.auth.dependencies import get_current_admin_user
from app.features.media.schemas import MediaUploadResponse
from app.features.media.service import upload_media

router = APIRouter()


@router.post("/upload", response_model=MediaUploadResponse, status_code=201)
def upload_file(
    file: UploadFile = File(...),
    folder: str = Form("general"),
    _=Depends(get_current_admin_user),
):
    return upload_media(file, folder=folder)
