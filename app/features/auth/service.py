import hashlib
import secrets
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
    return "".join(secrets.choice("0123456789") for _ in range(6))


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _create_otp(db: Session, email: str, purpose: str) -> str:
    now = datetime.now(timezone.utc)

    # Invalidate any previous unused OTPs for the same email + purpose
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.purpose == purpose,
        OTPCode.is_used == False,
    ).update({"is_used": True})

    # Remove expired records for this email to keep the table lean
    db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.expires_at < now,
    ).delete()

    code = _generate_otp()
    expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    otp = OTPCode(email=email, code=_hash_otp(code), purpose=purpose, expires_at=expires_at)
    db.add(otp)
    db.commit()
    return code  # return plaintext so it can be emailed


def _verify_otp(db: Session, email: str, code: str, purpose: str) -> OTPCode:
    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.email == email,
            OTPCode.code == _hash_otp(code),
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


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException()
    except JWTError:
        raise UnauthorizedException("Invalid refresh token")

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise UnauthorizedException()

    user = db.query(User).filter(User.id == uid).first()
    if not user or not user.is_active:
        raise UnauthorizedException("Account not found or is inactive")

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }


def forgot_password(db: Session, email: str) -> dict:
    # Always return the same message to prevent email enumeration
    user = db.query(User).filter(User.email == email).first()
    if user and user.is_verified:
        code = _create_otp(db, email, _OTP_PURPOSE_RESET)
        send_otp_email(email, code, _OTP_PURPOSE_RESET)
    return {"message": "If an account with that email exists, a reset code has been sent."}


def reset_password(db: Session, email: str, code: str, new_password: str) -> dict:
    # Verify OTP before looking up the user — prevents email enumeration:
    # a non-existent email has no OTP on record, so the error is identical
    # to a wrong OTP on a valid email ("Invalid OTP code").
    _verify_otp(db, email, code, _OTP_PURPOSE_RESET)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise BadRequestException("Invalid request")

    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"message": "Password has been reset successfully. You can now log in."}
