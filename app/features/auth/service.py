import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from jose import JWTError
from app.config import settings
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.exceptions import UnauthorizedException, ConflictException, BadRequestException
from app.core.email import send_otp_email
from app.features.users.models import User
from app.features.auth.models import OTPCode

_OTP_PURPOSE_VERIFY = "verify_email"
_OTP_PURPOSE_RESET = "reset_password"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _create_otp(db: Session, email: str, purpose: str) -> str:
    # Invalidate any previous unused OTPs for the same email + purpose
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == purpose,
        OTPCode.is_used == False,
    ).update({"is_used": True})

    code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    otp = OTPCode(email=email, code=code, purpose=purpose, expires_at=expires_at)
    db.add(otp)
    db.commit()
    return code


def _verify_otp(db: Session, email: str, code: str, purpose: str) -> OTPCode:
    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.email == email,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False,
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )
    if not otp:
        raise BadRequestException("Invalid OTP code")
    if datetime.now(timezone.utc) > otp.expires_at:
        raise BadRequestException("OTP code has expired")
    otp.is_used = True
    db.commit()
    return otp


def _token_pair(user: User) -> dict:
    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def register(db: Session, email: str, username: str, password: str) -> dict:
    if db.query(User).filter(User.email == email).first():
        raise ConflictException("An account with this email already exists")
    if db.query(User).filter(User.username == username).first():
        raise ConflictException("Username is already taken")

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        is_active=False,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    code = _create_otp(db, email, _OTP_PURPOSE_VERIFY)
    send_otp_email(email, code, _OTP_PURPOSE_VERIFY)
    return {"message": f"Account created. A verification code has been sent to {email}."}


def verify_email(db: Session, email: str, code: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise BadRequestException("No account found with this email")
    if user.is_verified:
        raise BadRequestException("Email is already verified")

    _verify_otp(db, email, code, _OTP_PURPOSE_VERIFY)

    user.is_verified = True
    user.is_active = True
    db.commit()
    db.refresh(user)
    return _token_pair(user)


def resend_verification_otp(db: Session, email: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise BadRequestException("No account found with this email")
    if user.is_verified:
        raise BadRequestException("Email is already verified")

    code = _create_otp(db, email, _OTP_PURPOSE_VERIFY)
    send_otp_email(email, code, _OTP_PURPOSE_VERIFY)
    return {"message": f"A new verification code has been sent to {email}."}


def login(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    if not user.is_verified:
        raise UnauthorizedException("Please verify your email before logging in")
    if not user.is_active:
        raise UnauthorizedException("Account is inactive")
    return _token_pair(user)


def refresh_tokens(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException()
    except JWTError:
        raise UnauthorizedException("Invalid refresh token")
    access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


def forgot_password(db: Session, email: str) -> dict:
    # Always return the same message to prevent email enumeration
    user = db.query(User).filter(User.email == email).first()
    if user and user.is_verified:
        code = _create_otp(db, email, _OTP_PURPOSE_RESET)
        send_otp_email(email, code, _OTP_PURPOSE_RESET)
    return {"message": "If an account with that email exists, a reset code has been sent."}


def reset_password(db: Session, email: str, code: str, new_password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise BadRequestException("Invalid request")

    _verify_otp(db, email, code, _OTP_PURPOSE_RESET)

    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"message": "Password has been reset successfully. You can now log in."}
