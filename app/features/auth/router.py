from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.auth import service
from app.features.auth.schemas import (
    LoginRequest, TokenResponse, RefreshRequest,
    RegisterRequest, MessageResponse,
    VerifyOTPRequest, ResendOTPRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)

router = APIRouter()


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return service.register(db, data.email, data.username, data.password)


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    return service.verify_email(db, data.email, data.code)


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(data: ResendOTPRequest, db: Session = Depends(get_db)):
    return service.resend_verification_otp(db, data.email)


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    return service.login(db, login_data.email, login_data.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_data: RefreshRequest):
    return service.refresh_tokens(refresh_data.refresh_token)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return service.forgot_password(db, data.email)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    return service.reset_password(db, data.email, data.code, data.new_password)
