from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.limiter import limiter, login_rate_limit_key
from app.dependencies import get_db
from app.features.auth import service
from app.features.auth.dependencies import get_current_user
from app.features.auth.schemas import (
    LoginRequest, TokenResponse, RefreshRequest,
    RegisterRequest, MessageResponse, FlowTokenResponse,
    VerifyOTPRequest, ResendOTPRequest,
    ForgotPasswordRequest, ForgotPasswordVerifyRequest, ResetPasswordRequest,
)

router = APIRouter()


@router.post("/register", response_model=MessageResponse, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    return service.register(db, data.email, data.full_name, data.password, data.phone_number, data.address)


@router.post("/verify-email", response_model=TokenResponse)
@limiter.limit("10/minute")
def verify_email(request: Request, data: VerifyOTPRequest, db: Session = Depends(get_db)):
    return service.verify_email(db, data.email, data.code)


@router.post("/resend-otp", response_model=MessageResponse)
@limiter.limit("5/minute")
def resend_otp(request: Request, data: ResendOTPRequest, db: Session = Depends(get_db)):
    return service.resend_verification_otp(db, data.email)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute", key_func=login_rate_limit_key)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    return service.login(db, login_data.email, login_data.password)


# OAuth2 form-based endpoint so Swagger UI "Authorize" works correctly.
# username field maps to email per OAuth2 convention.
@router.post("/token", response_model=TokenResponse, include_in_schema=False)
@limiter.limit("10/minute", key_func=login_rate_limit_key)
def token_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return service.login(db, form_data.username, form_data.password)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, refresh_data: RefreshRequest, db: Session = Depends(get_db)):
    return service.refresh_tokens(db, refresh_data.refresh_token)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("20/minute")
def logout(request: Request, _=Depends(get_current_user)):
    return service.logout()


@router.post("/forgot-password", response_model=FlowTokenResponse)
@limiter.limit("5/minute")
def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return service.forgot_password(db, data.email, data.type)


@router.post("/forgot-password/verification", response_model=FlowTokenResponse)
@limiter.limit("10/minute")
def forgot_password_verification(
    request: Request,
    data: ForgotPasswordVerifyRequest,
    db: Session = Depends(get_db),
):
    return service.forgot_password_verify(db, data.token, data.code)


@router.post("/reset-password", response_model=FlowTokenResponse)
@limiter.limit("5/minute")
def reset_password(request: Request, data: ResetPasswordRequest, db: Session = Depends(get_db)):
    return service.reset_password(db, data.token, data.password)
