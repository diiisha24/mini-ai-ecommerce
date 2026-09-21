from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ecommerce"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    google_client_id: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Stripe accounts registered as an individual in India can only accept payments in
    # INR - "usd" (the portable default for most Stripe accounts) gets rejected as an
    # "international payment" per RBI regulations. Override to "inr" if that's your account.
    stripe_currency: str = "usd"

    google_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    frontend_url: str = "http://localhost:5173"

    # Comma-separated list of emails that are granted the admin role on first login.
    admin_emails: str = ""

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
