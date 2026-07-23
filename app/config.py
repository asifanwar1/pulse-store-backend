from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5176"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@pulsestore.com"
    EMAILS_FROM_NAME: str = "Pulse Store"
    OTP_EXPIRE_MINUTES: int = 10

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "product-media"

    # Stripe (test/sandbox mode)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    DEFAULT_CURRENCY: str = "usd"

    # AI Agents
    AI_AGENTS_ENABLED: bool = True
    AI_DEFAULT_MODEL: str = "groq:llama-3.3-70b-versatile"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    AI_CHAT_MAX_HISTORY_TURNS: int = 20
    AI_REQUEST_TIMEOUT_SECONDS: float = 60.0
    AI_MAX_OUTPUT_TOKENS: int = 2000
    AI_MAX_MODEL_REQUESTS: int = 15
    """Caps tool-call round trips within a single chat turn (pydantic-ai's request_limit)."""

    # Firebase (push notifications)
    FIREBASE_CREDENTIALS_JSON: str = ""
    FIREBASE_PROJECT_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
