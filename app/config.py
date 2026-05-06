import os
from dotenv import load_dotenv

load_dotenv()

_database_url = os.getenv("DATABASE_URL")
if not _database_url:
    raise ValueError("DATABASE_URL is not set. Add it to your .env file.")

_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    raise ValueError("SECRET_KEY is not set. Add it to your .env file.")


class Settings:
    DATABASE_URL: str = _database_url
    SECRET_KEY: str = _secret_key
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Email / SMTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@pulsestore.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Pulse Store")
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))


settings = Settings()
