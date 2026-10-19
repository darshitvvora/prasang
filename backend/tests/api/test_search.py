"""Search reads come from Elasticsearch (test_ index prefix)."""
import pytest
from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.outbox.emit import artist_changed
from app.search.es import get_es
from app.search.projector import EsIndexer, project_batch, reindex_all
from tests.helpers import seed_demo


@pytest.fixture
async def indexed():
    await seed_demo()
    es = get_es()
    await reindex_all(get_sessionmaker(), es)
    yield es
    await es.close()


async def _total(client, qs=""):
    res = await client.get(f"/api/v1/search/artists?{qs}")
    assert res.status_code == 200, res.text
    return res.json()


async def test_search_filters(client, indexed):
    assert (await _total(client))["total"] == 12
    assert (await _total(client, "artistType=dj"))["total"] == 2
    assert (await _total(client, "city=Pune"))["total"] == 2
    assert (await _total(client, "featuredOnly=true"))["total"] == 4
    assert all(a["averageRating"] >= 4.8 for a in (await _total(client, "minRating=4.8"))["items"])
    prices = [a["perEventRateMin"] for a in (await _total(client, "sort=price_low"))["items"]]
    assert prices == sorted(prices)


async def test_text_search_and_facets(client, indexed):
    body = await _total(client, "q=magician")
    assert body["items"][0]["artistType"] == "magician"
    facets = {b["value"]: b["count"] for b in (await _total(client))["facets"]["artistType"]}
    assert facets["dj"] == 2 and facets["singer"] == 3
    typo = await _total(client, "q=magican")
    assert any(a["artistType"] == "magician" for a in typo["items"])


async def test_cards_match_contract_and_hide_contacts(client, indexed):
    item = (await _total(client, "artistType=band"))["items"][0]
    assert "contactPhone" not in item and "media" not in item
    assert item["slug"] == "the-raaga-collective"


async def test_suggestions_featured_similar(client, indexed):
    sug = (await client.get("/api/v1/search/suggestions?q=dj")).json()["items"]
    assert {"type": "artistType", "label": "DJ", "value": "dj", "slug": None} in sug
    assert any(s["type"] == "artist" and s["slug"] == "dj-krish" for s in sug)
    area = (await client.get("/api/v1/search/suggestions?q=band")).json()["items"]
    assert any(s["type"] == "area" and s["value"] == "Bandra West" for s in area)

    featured = (await client.get("/api/v1/artists/featured")).json()["items"]
    assert featured and all(a["isFeatured"] for a in featured)

    similar = (await client.get("/api/v1/artists/arjun-malhotra-magic/similar")).json()["items"]
    assert similar and all(a["slug"] != "arjun-malhotra-magic" for a in similar)
    assert similar[0]["artistType"] == "magician"


async def test_profile_change_becomes_searchable(client, indexed):
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "dj-krish"))).scalar_one()
        artist.location_city = "Goa"
        artist_changed(s, artist.id)
        await s.commit()
    await project_batch(get_sessionmaker(), EsIndexer(indexed, refresh=True))
    assert (await _total(client, "city=Goa"))["total"] == 1
