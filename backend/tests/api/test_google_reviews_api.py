import pytest
from sqlalchemy import select

from app.admin import actions
from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.reviews.google import GoogleReview, GoogleReviews
from tests.helpers import ARTIST, seed_demo

ARJUN = "arjun-malhotra-magic"


class FakePlaces:
    async def resolve_place_id(self, url: str) -> str | None:
        return "ChIJfake"

    async def reviews(self, place_id: str) -> GoogleReviews | None:
        items = [GoogleReview(author=f"G{i}", rating=5, relative_time="a week ago", text="Lovely") for i in range(5)]
        return GoogleReviews(rating=4.8, count=90, maps_url="https://maps.google.com/?cid=9", items=items)


@pytest.fixture
def places(monkeypatch):
    fake = FakePlaces()
    monkeypatch.setattr("app.reviews.google.get_places", lambda: fake)
    return fake


async def test_saving_link_resolves_place_and_endpoint_returns_reviews(client, places):
    await seed_demo()
    res = await client.patch("/api/v1/artists/me", headers=ARTIST, json={"googlePlaceUrl": "https://maps.app.goo.gl/AbC"})
    assert res.status_code == 200 and res.json()["googlePlaceUrl"] == "https://maps.app.goo.gl/AbC"
    body = (await client.get(f"/api/v1/artists/{ARJUN}/google-reviews")).json()
    assert (body["rating"], body["count"], len(body["items"])) == (4.8, 90, 5)
    assert body["items"][0] == {"author": "G0", "rating": 5, "relativeTime": "a week ago", "text": "Lovely"}


async def test_endpoint_204_without_key(client, monkeypatch):
    monkeypatch.setattr("app.reviews.google.get_places", lambda: None)
    await seed_demo()
    await client.patch("/api/v1/artists/me", headers=ARTIST, json={"googlePlaceUrl": "https://maps.app.goo.gl/AbC"})
    res = await client.get(f"/api/v1/artists/{ARJUN}/google-reviews")
    assert res.status_code == 204


async def test_endpoint_204_without_place(client, places):
    await seed_demo()
    assert (await client.get(f"/api/v1/artists/{ARJUN}/google-reviews")).status_code == 204


async def test_invalid_url_422(client, places):
    await seed_demo()
    res = await client.patch("/api/v1/artists/me", headers=ARTIST, json={"googlePlaceUrl": "https://evil.example.com/maps/place/x"})
    assert res.status_code == 422 and "googlePlaceUrl" in res.json()["error"]["details"]["fields"]


async def test_clearing_link_removes_place(client, places):
    await seed_demo()
    await client.patch("/api/v1/artists/me", headers=ARTIST, json={"googlePlaceUrl": "https://maps.app.goo.gl/AbC"})
    res = await client.patch("/api/v1/artists/me", headers=ARTIST, json={"googlePlaceUrl": None})
    assert res.status_code == 200 and res.json()["googlePlaceUrl"] is None
    assert (await client.get(f"/api/v1/artists/{ARJUN}/google-reviews")).status_code == 204


async def test_clear_google_place_cli(client, places):
    await seed_demo()
    await client.patch("/api/v1/artists/me", headers=ARTIST, json={"googlePlaceUrl": "https://maps.app.goo.gl/AbC"})
    async with get_sessionmaker()() as s:
        await actions.clear_google_place(s, ARJUN, actor="test")
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        assert (artist.google_place_url, artist.google_place_id) == (None, None)
