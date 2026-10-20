import json
from pathlib import Path

from sqlalchemy import select

from app.db import get_sessionmaker
from app.outbox.models import OutboxEvent
from tests.helpers import ARTIST, NEW, PLANNER, seed_demo

EXAMPLE = json.loads((Path(__file__).resolve().parents[3] / "contracts/examples/artists/post.request.json").read_text())


async def _new_artist(client):
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Tanvi Rao"})


async def _outbox(aggregate_id: str) -> list[str]:
    async with get_sessionmaker()() as s:
        rows = (await s.execute(select(OutboxEvent.event_type).where(OutboxEvent.aggregate_id == aggregate_id))).scalars()
        return list(rows)


async def test_create_profile(client):
    await _new_artist(client)
    res = await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"name": "Tanvi Rao Live"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "tanvi-rao-live"
    assert (body["isPublished"], body["subscriptionTier"], body["contactPhone"]) == (False, "free", "9820011001")
    assert body["completeness"]["percent"] > 0
    assert body["socialWidgets"] == []  # new artists start on Free: social links are plain text (2026-10-20 plans)
    assert body["instagramHandle"] and body["youtubeChannel"]
    assert await _outbox(body["artistId"]) == ["artist.upserted"]

    me = await client.get("/api/v1/me", headers=NEW)
    assert me.json()["artistSlug"] == "tanvi-rao-live"
    again = await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE)
    assert again.status_code == 409 and again.json()["error"]["code"] == "artist_exists"


async def test_slug_collision_gets_suffix(client):
    await seed_demo()
    await _new_artist(client)
    res = await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"name": "Arjun Malhotra Magic"})  # collides with seeded slug
    assert res.status_code == 201
    slug = res.json()["slug"]
    assert slug.startswith("arjun-malhotra") and slug != "arjun-malhotra-magic"


async def test_planner_cannot_create_artist_profile(client):
    await seed_demo()
    res = await client.post("/api/v1/artists", headers=PLANNER, json=EXAMPLE)
    assert res.status_code == 403


async def test_validation_errors(client):
    await _new_artist(client)
    bad = EXAMPLE | {"perEventRateMin": 30000, "perEventRateMax": 20000}
    res = await client.post("/api/v1/artists", headers=NEW, json=bad)
    assert res.status_code == 422 and "perEventRateMax" in res.json()["error"]["details"]["fields"]
    res = await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"contactPhone": "123"})
    assert "contactPhone" in res.json()["error"]["details"]["fields"]
    res = await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"facebookUrl": "https://evil.example/arjun"})
    assert "facebookUrl" in res.json()["error"]["details"]["fields"]
    res = await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"instagramHandle": "not a handle"})
    assert "instagramHandle" in res.json()["error"]["details"]["fields"]


async def test_get_own_profile_before_create(client):
    await _new_artist(client)
    res = await client.get("/api/v1/artists/me", headers=NEW)
    assert res.status_code == 404 and res.json()["error"]["code"] == "artist_profile_not_found"


async def test_patch_profile_and_publish(client):
    await _new_artist(client)
    created = (await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE)).json()
    res = await client.patch("/api/v1/artists/me", headers=NEW,
                             json={"bio": "New bio", "facebookUrl": "facebook.com/tanvi.live", "isPublished": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["bio"], body["facebookUrl"], body["isPublished"]) == ("New bio", "https://www.facebook.com/tanvi.live", True)
    assert await _outbox(created["artistId"]) == ["artist.upserted", "artist.upserted"]
    bad = await client.patch("/api/v1/artists/me", headers=NEW, json={"perEventRateMax": 1})
    assert bad.status_code == 422 and "perEventRateMax" in bad.json()["error"]["details"]["fields"]


async def test_seeded_artist_profile(client):
    await seed_demo()
    res = await client.get("/api/v1/artists/me", headers=ARTIST)
    assert res.status_code == 200
    assert res.json()["slug"] == "arjun-malhotra-magic"
