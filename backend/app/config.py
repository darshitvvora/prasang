"""Application settings from environment variables (see .env.example)."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["local", "test", "production"] = "local"
    database_url: str = "postgresql+asyncpg://prasang:prasang@localhost:5433/prasang"
    db_pool_size: int = 5

    elasticsearch_url: str = "http://localhost:9200"
    es_index_prefix: str = ""

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "prasang"

    supertokens_uri: str = "http://localhost:3567"
    supertokens_api_key: str = "local-supertokens-key"
    # Browser-facing origins. Locally the Vite dev server proxies /api, so both are the web origin.
    api_domain: str = "http://localhost:5173"
    website_domain: str = "http://localhost:5173"
    cookie_domain: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    dev_auth_header: bool = False
    youtube_api_key: str | None = None  # optional: resolves @handles to channel ids for the YouTube widget

    aws_region: str = "ap-south-1"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None  # only for tests (moto); real S3 uses the AWS default endpoint
    public_media_base_url: str | None = None  # defaults to https://<bucket>.s3.<region>.amazonaws.com

    payment_gateway: Literal["fake", "razorpay"] = "fake"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    notifier: Literal["console", "msg91"] = "console"
    msg91_auth_key: str | None = None
    msg91_sms_template_id: str | None = None  # DLT-approved template with a ##message## variable
    msg91_whatsapp_number: str | None = None
    resend_api_key: str | None = None
    email_sender: str = "Prasang <leads@prasang.in>"

    # Public web origin used in links inside messages and share previews.
    public_web_url: str = "http://localhost:5173"
    support_email: str | None = None  # contact-form messages are emailed here
    support_phone: str | None = None
    business_address: str | None = None

    cors_origins: list[str] = ["http://localhost:5173"]
    # Repo root containing contracts/ and mockoon/data (seed datasets). Docker mounts them at /seed.
    seed_root: str = str(Path(__file__).resolve().parents[2])

    def validate_for_env(self) -> None:
        if self.env == "production" and self.dev_auth_header:
            raise ValueError("DEV_AUTH_HEADER must never be enabled in production")
        public = [d for d in (self.api_domain, self.website_domain) if d.startswith("https://") and "localhost" not in d]
        if public and self.env != "production":
            # Fail closed: public HTTPS domains mean a real deployment, which needs secure cookies and no dev shortcuts.
            raise ValueError(f"{public[0]} is a public domain — set ENV=production")

    @property
    def es_alias(self) -> str:
        return f"{self.es_index_prefix}artists"

    @property
    def media_base_url(self) -> str | None:
        if self.public_media_base_url:
            return self.public_media_base_url.rstrip("/")
        if self.s3_bucket:
            return f"https://{self.s3_bucket}.s3.{self.aws_region}.amazonaws.com"
        return None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_for_env()
    return settings
