from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.artists.models import ArtistDailyStat, ArtistProfile
from app.artists.stats import today_ist
from app.db import get_sessionmaker
from app.leads.usage import month_bounds_ist
from tests.helpers import ARTIST, seed_demo


async def _arjun_id():
    async with get_sessionmaker()() as s:
        return (await s.execute(select(ArtistProfile.id).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()


async def test_public_profile_hides_contacts_and_counts_views(client):
    await seed_demo()
    res = await client.get("/api/v1/artists/arjun-malhotra-magic")
    assert res.status_code == 200
    body = res.json()
    assert "contactPhone" not in body and "whatsappNumber" not in body
    assert len(body["media"]) == 4 and body["socialWidgets"]
    await client.get("/api/v1/artists/arjun-malhotra-magic")
    async with get_sessionmaker()() as s:
        stat = await s.get(ArtistDailyStat, (await _arjun_id(), today_ist()))
    assert stat.profile_views == 2


async def test_unknown_or_unpublished_profile_is_404(client):
    await seed_demo()
    assert (await client.get("/api/v1/artists/nobody")).json()["error"]["code"] == "artist_not_found"
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "dj-krish"))).scalar_one()
        artist.is_published = False
        await s.commit()
    assert (await client.get("/api/v1/artists/dj-krish")).status_code == 404


async def test_contact_click(client):
    await seed_demo()
    res = await client.post("/api/v1/artists/arjun-malhotra-magic/contact-click")
    assert res.status_code == 204
    async with get_sessionmaker()() as s:
        stat = await s.get(ArtistDailyStat, (await _arjun_id(), today_ist()))
    assert stat.contact_clicks == 1
    assert (await client.post("/api/v1/artists/nobody/contact-click")).status_code == 404


async def test_dashboard(client):
    await seed_demo()
    artist_id = await _arjun_id()
    start, _ = month_bounds_ist(datetime.now(UTC))
    this_day = start.date() + timedelta(days=1)
    last_day = start.date() - timedelta(days=3)
    async with get_sessionmaker()() as s:
        s.add_all([ArtistDailyStat(artist_id=artist_id, day=this_day, profile_views=150, contact_clicks=12),
                   ArtistDailyStat(artist_id=artist_id, day=last_day, profile_views=100, contact_clicks=0)])
        await s.commit()
    res = await client.get("/api/v1/artists/me/dashboard", headers=ARTIST)
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["greetingName"] == "Arjun" and d["isPublished"] is True
    assert d["metrics"]["profileViews"] == {"value": 150, "changePct": 50}
    assert d["metrics"]["contactClicks"] == {"value": 12, "changePct": None}
    assert d["plan"]["tier"] == "basic" and d["plan"]["leadLimitMonthly"] == 15
    assert len(d["recentLeads"]) == 3
    locked = [lead for lead in d["recentLeads"] if lead["isLocked"]]
    assert all(lead["plannerPhone"] is None and lead["plannerEmail"] is None for lead in locked)
    assert sum(s["pct"] for s in d["leadSources"]) in (0, 99, 100, 101)
