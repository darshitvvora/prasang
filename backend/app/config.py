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
    google_places_api_key: str | None = None  # optional: shows Google reviews from the artist's listing
    youtube_api_key: str | None = None  # optional: resolves @handles to channel ids for the YouTube widget

    aws_region: str = "ap-south-1"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None  # only for tests (moto); real S3 uses the AWS default endpoint
    public_media_base_url: str | None = None  # defaults to https://<bucket>.s3.<region>.amazonaws.com

    # PhonePe Payment Links: one link per billing period, emailed/texted to the artist; a webhook marks it paid.
    # auto = PhonePe as soon as PHONEPE_CLIENT_ID and PHONEPE_CLIENT_SECRET are set, otherwise the fake.
    payment_gateway: Literal["auto", "fake", "phonepe"] = "auto"
    phonepe_env: Literal["sandbox", "production"] = "sandbox"
    phonepe_client_id: str | None = None
    phonepe_client_secret: str | None = None
    phonepe_client_version: str = "1"
    phonepe_webhook_username: str | None = None  # set on the PhonePe dashboard webhook (SHA256 auth)
    phonepe_webhook_password: str | None = None

    # SMS + WhatsApp via MSG91. auto = on as soon as MSG91_AUTH_KEY is set, otherwise everything is logged.
    # One template per message type: WhatsApp (no DLT) and/or SMS (DLT only); see `python -m app.cli msg91-templates`.
    notifier: Literal["auto", "console", "msg91"] = "auto"
    msg91_auth_key: str | None = None
    msg91_short_url: bool = True  # let MSG91 shorten links (keeps link variables within DLT limits)
    msg91_sms_template_otp: str | None = None
    msg91_sms_template_lead: str | None = None
    msg91_sms_template_lead_locked: str | None = None
    msg91_sms_template_welcome_artist: str | None = None
    msg91_sms_template_welcome_planner: str | None = None
    msg91_sms_template_trial_ending: str | None = None
    msg91_sms_template_payment_link: str | None = None
    msg91_sms_template_renewal_due: str | None = None
    msg91_sms_template_payment_received: str | None = None
    msg91_sms_template_plan_ended: str | None = None
    msg91_sms_template_media_removal: str | None = None
    msg91_sms_template_booking_check: str | None = None
    msg91_whatsapp_number: str | None = None  # integrated WhatsApp number with country code, e.g. 919820000000
    # WhatsApp template *names* (Meta-approved) in MSG91 → WhatsApp → Templates
    msg91_whatsapp_template_otp: str | None = None
    msg91_whatsapp_template_lead: str | None = None
    msg91_whatsapp_template_lead_locked: str | None = None
    msg91_whatsapp_template_welcome_artist: str | None = None
    msg91_whatsapp_template_welcome_planner: str | None = None
    msg91_whatsapp_template_trial_ending: str | None = None
    msg91_whatsapp_template_payment_link: str | None = None
    msg91_whatsapp_template_renewal_due: str | None = None
    msg91_whatsapp_template_payment_received: str | None = None
    msg91_whatsapp_template_plan_ended: str | None = None
    msg91_whatsapp_template_media_removal: str | None = None
    msg91_whatsapp_template_booking_check: str | None = None
    msg91_whatsapp_language: str = "en"
    # Email over SMTP (SendPulse: smtp-pulse.com, port 465 = implicit TLS, 587/2525 = STARTTLS). Unset = log only.
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_sender: str = "Prasang <hello@prasang.in>"

    # Public web origin used in links inside messages and share previews.
    public_web_url: str = "http://localhost:5173"
    web_index_path: str | None = None  # built web app index.html; served with preview tags at /profile/{slug}
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

    def msg91_templates(self, channel: Literal["sms", "whatsapp"]) -> dict[str, str]:
        """kind -> MSG91 template id (SMS) / name (WhatsApp), for the kinds configured so far."""
        from app.notifications.texts import SMS_TEMPLATES, WHATSAPP_KINDS

        kinds = SMS_TEMPLATES if channel == "sms" else WHATSAPP_KINDS
        found = {k: getattr(self, f"msg91_{channel}_template_{k}", None) for k in kinds}
        return {k: v for k, v in found.items() if v}

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
