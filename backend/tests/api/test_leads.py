import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.db import get_sessionmaker
from app.leads.models import Lead
from tests.helpers import ARTIST, PLANNER, seed_demo


def lead_body(artist_id: str, **kw) -> dict:
    return {"artistId": artist_id, "plannerName": "Neha Kulkarni", "plannerPhone": "9920012345", "plannerEmail": None,
            "eventType": "wedding", "eventDate": None, "eventCity": "Mumbai", "budgetRange": "15k_25k", "notes": None,
            "source": "profile"} | kw


async def artist_id(client, slug: str) -> str:
    return (await client.get(f"/api/v1/artists/{slug}")).json()["artistId"]


async def test_auth_and_role_rules(client):
    await seed_demo()
    aid = await artist_id(client, "dj-krish")
    assert (await client.post("/api/v1/leads", json=lead_body(aid))).status_code == 401
    assert (await client.post("/api/v1/leads", headers=ARTIST, json=lead_body(aid))).status_code == 403
    missing = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body("00000000-0000-0000-0000-000000000000"))
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "artist_not_found"


async def test_create_returns_contact_and_dedupes(client):
    await seed_demo()
    aid = await artist_id(client, "dj-krish")
    when = (date.today() + timedelta(days=30)).isoformat()
    res = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=when))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["artist"] == {"name": "DJ Krish", "contactPhone": "9820011002", "whatsappNumber": "9820011002", "instagramHandle": "djkrish_official"}
    again = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=when, notes="changed"))
    assert again.status_code == 200 and again.json()["leadId"] == body["leadId"]


async def test_daily_rate_limit(client):
    await seed_demo()
    aid = await artist_id(client, "dj-krish")
    base = date.today() + timedelta(days=60)
    for i in range(10):
        res = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=(base + timedelta(days=i)).isoformat()))
        assert res.status_code == 201
    res = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=(base + timedelta(days=99)).isoformat()))
    assert res.status_code == 429 and res.json()["error"]["code"] == "lead_rate_limited"


async def test_concurrent_leads_respect_free_quota(client):
    """Review Focus 1: 6 simultaneous contacts to a Free artist (3/month) → exactly 3 unlocked, planner always gets contact."""
    await seed_demo()
    aid = await artist_id(client, "kabir-mentalist")
    base = date.today() + timedelta(days=10)
    results = await asyncio.gather(*[
        client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=(base + timedelta(days=i)).isoformat()))
        for i in range(6)])
    assert all(r.status_code == 201 and r.json()["artist"]["contactPhone"] for r in results)
    async with get_sessionmaker()() as s:
        leads = (await s.execute(select(Lead).where(Lead.artist_id == aid))).scalars().all()
    assert len(leads) == 6 and sum(not lead.is_locked for lead in leads) == 3


async def test_artist_leads_view(client):
    await seed_demo()
    res = await client.get("/api/v1/leads/artist", headers=ARTIST)
    assert res.status_code == 200
    body = res.json()
    assert body["counts"]["all"] == body["total"] == 8
    locked = [lead for lead in body["items"] if lead["isLocked"]]
    assert len(locked) == 1 and locked[0]["plannerPhone"] is None and locked[0]["plannerEmail"] is None
    assert body["plan"]["tier"] == "pro"
    new_only = (await client.get("/api/v1/leads/artist?status=new", headers=ARTIST)).json()
    assert all(lead["status"] == "new" for lead in new_only["items"]) and new_only["total"] == body["counts"]["new"]
    assert (await client.get("/api/v1/leads/artist", headers=PLANNER)).status_code == 403


async def test_status_transitions(client):
    await seed_demo()
    items = (await client.get("/api/v1/leads/artist?status=new", headers=ARTIST)).json()["items"]
    lead = next(i for i in items if not i["isLocked"])
    res = await client.patch(f"/api/v1/leads/{lead['id']}", headers=ARTIST, json={"status": "contacted"})
    assert res.status_code == 200 and res.json()["status"] == "contacted"
    assert (await client.patch(f"/api/v1/leads/{lead['id']}", headers=ARTIST, json={"status": "converted"})).json()["status"] == "converted"
    bad = await client.patch(f"/api/v1/leads/{lead['id']}", headers=ARTIST, json={"status": "new"})
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "invalid_transition"
    assert (await client.patch("/api/v1/leads/00000000-0000-0000-0000-000000000000", headers=ARTIST, json={"status": "contacted"})).status_code == 404


async def test_planner_inquiries(client):
    await seed_demo()
    res = await client.get("/api/v1/leads/planner", headers=PLANNER)
    assert res.status_code == 200
    body = res.json()
    assert body["counts"] == {"all": 5, "pending": 2, "responded": 1, "confirmed": 1, "declined": 1}
    assert body["summary"]["artistsContacted"] == 5 and body["summary"]["confirmedBookings"] == 1
    assert body["items"][0]["artist"]["slug"]
    pending = (await client.get("/api/v1/leads/planner?status=pending", headers=PLANNER)).json()
    assert pending["total"] == 2 and all(i["status"] == "pending" for i in pending["items"])
    assert (await client.get("/api/v1/leads/planner", headers=ARTIST)).status_code == 403


async def test_expire_leads(client):
    from app.leads.service import expire_leads
    await seed_demo()
    async with get_sessionmaker()() as s:
        expired = await expire_leads(s, today=date(2030, 1, 1))
    assert expired > 0
    body = (await client.get("/api/v1/leads/artist?status=new", headers=ARTIST)).json()
    assert all(lead["eventDate"] is None for lead in body["items"])
