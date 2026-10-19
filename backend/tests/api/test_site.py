from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.db import get_sessionmaker
from app.site.models import ContactMessage
from app.site.router import contact_notifier

MESSAGE = {"name": "Riya Shah", "contact": "riya@example.com", "topic": "payments", "message": "I paid but the plan is still Free."}


class SpyNotifier:
    def __init__(self):
        self.emails: list[tuple[str, str, str]] = []

    async def send_email(self, to: str, subject: str, text: str) -> None:
        self.emails.append((to, subject, text))


def _client(settings: Settings, spy: SpyNotifier | None = None) -> AsyncClient:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[contact_notifier] = lambda: spy or SpyNotifier()
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _settings(**kw) -> Settings:
    return Settings(env="test", dev_auth_header=True, **kw)


async def _count() -> int:
    async with get_sessionmaker()() as s:
        return (await s.execute(select(func.count()).select_from(ContactMessage))).scalar_one()


async def test_site_info_returns_configured_values():
    settings = _settings(support_email="hello@prasang.in", support_phone="9820012345", business_address="Andheri West, Mumbai")
    async with _client(settings) as c:
        res = await c.get("/api/v1/site-info")
    assert res.status_code == 200
    assert res.json() == {"supportEmail": "hello@prasang.in", "supportPhone": "9820012345", "businessAddress": "Andheri West, Mumbai"}


async def test_contact_stores_and_emails():
    spy = SpyNotifier()
    async with _client(_settings(support_email="hello@prasang.in"), spy) as c:
        res = await c.post("/api/v1/contact", json=MESSAGE)
    assert res.status_code == 201
    assert res.json()["id"]
    assert await _count() == 1
    [(to, subject, text)] = spy.emails
    assert to == "hello@prasang.in"
    assert subject.startswith("Contact: ")
    assert "I paid but the plan is still Free." in text and "riya@example.com" in text


async def test_contact_without_support_email_only_stores():
    spy = SpyNotifier()
    async with _client(_settings(support_email=None), spy) as c:
        res = await c.post("/api/v1/contact", json=MESSAGE)
    assert res.status_code == 201
    assert await _count() == 1
    assert spy.emails == []


async def test_contact_rate_limited_after_5_per_ip_per_hour():
    async with _client(_settings()) as c:
        for _ in range(5):
            assert (await c.post("/api/v1/contact", json=MESSAGE)).status_code == 201
        res = await c.post("/api/v1/contact", json=MESSAGE)
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "contact_rate_limited"


async def test_contact_validation():
    async with _client(_settings()) as c:
        res = await c.post("/api/v1/contact", json={**MESSAGE, "message": "short"})
    assert res.status_code == 422
    assert "message" in res.json()["error"]["details"]["fields"]
