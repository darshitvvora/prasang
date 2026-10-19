"""Admin actions as seen through the API and search: suspended artists disappear everywhere and stay gone."""
import pytest
from sqlalchemy import select

from app.admin import actions
from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.search.es import alias, get_es
from app.search.projector import EsIndexer, project_batch, reindex_all
from tests.helpers import ARTIST, PLANNER, seed_demo

SLUG = "arjun-malhotra-magic"


@pytest.fixture
async def indexed():
    await seed_demo()
    es = get_es()
    await reindex_all(get_sessionmaker(), es)
    yield es
    await es.close()


async def _in_index(es, slug: str) -> bool:
    await es.indices.refresh(index=alias())
    res = await es.search(index=alias(), body={"query": {"term": {"slug": slug}}})
    return res["hits"]["total"]["value"] > 0


async def _project(es) -> None:
    await project_batch(get_sessionmaker(), EsIndexer(es))


async def _act(fn, *args, **kw):
    async with get_sessionmaker()() as s:
        await fn(s, *args, actor="test", **kw)


async def test_suspend_hides_from_public_search_and_similar(client, indexed):
    await _act(actions.suspend, SLUG, reason="Fake reviews under investigation")
    assert (await client.get(f"/api/v1/artists/{SLUG}")).status_code == 404
    await _project(indexed)
    assert not await _in_index(indexed, SLUG)

    await reindex_all(get_sessionmaker(), indexed)
    assert not await _in_index(indexed, SLUG)

    res = await client.patch("/api/v1/artists/me", headers=ARTIST, json={"bio": "New bio after suspension, still hidden."})
    assert res.status_code == 200
    await _project(indexed)
    assert not await _in_index(indexed, SLUG)


async def test_restore_brings_back(client, indexed):
    await _act(actions.suspend, SLUG, reason="check")
    await _act(actions.restore, SLUG)
    assert (await client.get(f"/api/v1/artists/{SLUG}")).status_code == 200
    await _project(indexed)
    assert await _in_index(indexed, SLUG)


async def test_suspended_artist_rejects_new_leads(client, indexed):
    artist_id = (await client.get(f"/api/v1/artists/{SLUG}")).json()["artistId"]
    await _act(actions.suspend, SLUG, reason="check")
    res = await client.post("/api/v1/leads", headers=PLANNER, json={
        "artistId": artist_id, "plannerName": "Neha", "plannerPhone": "9820011111", "plannerEmail": None,
        "eventType": "birthday", "eventDate": None, "eventCity": "Mumbai", "budgetRange": "10k_15k", "notes": None,
        "source": "search"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "artist_suspended"


async def test_own_profile_shows_suspension_reason(client, indexed):
    await _act(actions.suspend, SLUG, reason="Profile photo is not you")
    body = (await client.get("/api/v1/artists/me", headers=ARTIST)).json()
    assert body["suspended"] is True
    assert body["suspensionReason"] == "Profile photo is not you"


async def test_block_user_rejects_requests(client, monkeypatch):
    await seed_demo()
    monkeypatch.setattr("app.admin.actions.revoke_sessions", _noop_revoke)
    await _act(actions.block_user, "dev-planner-neha", reason="Spam inquiries")
    res = await client.get("/api/v1/me", headers=PLANNER)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "account_blocked"

    await _act(actions.unblock_user, "dev-planner-neha")
    assert (await client.get("/api/v1/me", headers=PLANNER)).status_code == 200


async def test_feature_override_survives_plan_change(client, indexed):
    async with get_sessionmaker()() as s:
        from app.subscriptions.service import downgrade_to_free

        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == SLUG))).scalar_one()
        await downgrade_to_free(s, artist)
        await s.commit()
        assert artist.is_featured is False
    await _act(actions.set_featured, SLUG, True)
    async with get_sessionmaker()() as s:
        from app.subscriptions.service import downgrade_to_free

        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == SLUG))).scalar_one()
        assert artist.is_featured is True
        await downgrade_to_free(s, artist)
        await s.commit()
        assert artist.is_featured is True
    await _act(actions.set_featured, SLUG, False)
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == SLUG))).scalar_one()
        assert artist.is_featured is False


async def _noop_revoke(user_id: str) -> None:
    return None
