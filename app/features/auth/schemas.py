from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


def _validate_otp_digits(v: str) -> str:
    if not v.isdigit() or len(v) != 6:
        raise ValueError("OTP must be exactly 6 digits")
    return v


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


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return _validate_otp_digits(v)
