"""Local-only reset so smoke tests (mockoon/smoke.sh) can run repeatedly against the real API."""
from sqlalchemy import func, select

from app.config import get_settings
from app.db import get_sessionmaker
from app.leads.models import Lead
from tests.helpers import NEW, PLANNER, seed_demo


async def test_reset_restores_demo_world(client):
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "planner", "fullName": "Temp"})
    await client.patch("/api/v1/me", headers=PLANNER, json={"fullName": "Changed"})
    res = await client.post("/api/v1/_mock/reset")
    assert res.status_code == 200
    assert (await client.get("/api/v1/me", headers=NEW)).status_code == 404
    assert (await client.get("/api/v1/me", headers=PLANNER)).json()["fullName"] == "Neha Kulkarni"
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(func.count()).select_from(Lead))).scalar_one() == 12


async def test_reset_is_unavailable_without_dev_auth(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "dev_auth_header", False)
    assert (await client.post("/api/v1/_mock/reset")).status_code == 404


async def test_reset_clears_contact_messages(client):
    """The smoke test posts a contact message each run; reset keeps it under the per-IP limit."""
    from sqlalchemy import func, select

    from app.db import get_sessionmaker
    from app.site.models import ContactMessage

    await seed_demo()
    body = {"name": "Smoke", "contact": "9820012345", "topic": "general", "message": "Hello from the smoke test"}
    assert (await client.post("/api/v1/contact", json=body)).status_code == 201
    assert (await client.post("/api/v1/_mock/reset")).status_code == 200
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(func.count()).select_from(ContactMessage))).scalar_one() == 0
