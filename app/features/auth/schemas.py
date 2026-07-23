from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.features.users.schemas import Address


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="token")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(default="bearer", alias="tokentype")


class RefreshRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refreshToken")


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    phone_number: str | None = None
    address: Address = Field(default_factory=Address)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class MessageResponse(BaseModel):
    message: str


class FlowTokenResponse(BaseModel):
    token: str


def _validate_otp_digits(v: str) -> str:
    if not v.isdigit() or len(v) != 4:
        raise ValueError("OTP must be exactly 4 digits")
    return v


def _validate_password_strength(v: str) -> str:
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in v):
        raise ValueError("Password must contain at least one special character")
    return v


_ALLOWED_USER_TYPES = {"CUSTOMER", "VENDOR", "ADMIN"}


def _validate_user_type(v: str) -> str:
    normalized = v.strip().upper()
    if normalized not in _ALLOWED_USER_TYPES:
        raise ValueError("type must be one of: CUSTOMER, VENDOR, ADMIN")
    return normalized


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return _validate_otp_digits(v)


class ResendOTPRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        return _validate_user_type(v)


class ForgotPasswordVerifyRequest(BaseModel):
    token: str = Field(min_length=1)
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return _validate_otp_digits(v)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)
