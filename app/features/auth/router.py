from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.auth import service
from app.features.auth.schemas import LoginRequest, TokenResponse, RefreshRequest

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    return service.login(db, login_data.email, login_data.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_data: RefreshRequest):
    return service.refresh_tokens(refresh_data.refresh_token)
