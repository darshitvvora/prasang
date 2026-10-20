import httpx
import pytest

from app.reviews.google import GooglePlaces, clear_cache, is_google_maps_url

PLACE = {
    "rating": 4.7, "userRatingCount": 212, "googleMapsUri": "https://maps.google.com/?cid=123",
    "reviews": [{"authorAttribution": {"displayName": f"Guest {i}"}, "rating": 5,
                 "relativePublishTimeDescription": "2 weeks ago", "text": {"text": f"Great show {i}"}} for i in range(7)],
}


def _client(calls: list[str], short_target="https://www.google.com/maps/place/Arjun+Magic/@19.1,72.8,17z") -> GooglePlaces:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url}")
        if request.url.host == "maps.app.goo.gl":
            return httpx.Response(302, headers={"location": short_target})
        if request.url.path == "/v1/places:searchText":
            assert request.headers["X-Goog-FieldMask"] == "places.id"
            return httpx.Response(200, json={"places": [{"id": "ChIJsearch"}]})
        if request.url.path.startswith("/v1/places/"):
            assert request.headers["X-Goog-Api-Key"] == "key"
            return httpx.Response(200, json=PLACE)
        return httpx.Response(404)

    return GooglePlaces("key", httpx.AsyncClient(transport=httpx.MockTransport(handler)))


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()


async def test_resolve_from_full_maps_url():
    calls: list[str] = []
    places = _client(calls)
    assert await places.resolve_place_id("https://www.google.com/maps/place/?q=place_id:ChIJdirect") == "ChIJdirect"
    assert await places.resolve_place_id("https://www.google.com/maps/search/?api=1&query=x&query_place_id=ChIJquery") == "ChIJquery"
    assert await places.resolve_place_id("https://www.google.com/maps/place/Arjun+Magic/@19.1,72.8,17z") == "ChIJsearch"
    assert calls == ["POST https://places.googleapis.com/v1/places:searchText"]


async def test_resolve_follows_short_link():
    calls: list[str] = []
    assert await _client(calls).resolve_place_id("https://maps.app.goo.gl/AbCdEf123") == "ChIJsearch"
    assert calls[0] == "GET https://maps.app.goo.gl/AbCdEf123"


async def test_reviews_cached_24h():
    calls: list[str] = []
    places = _client(calls)
    first = await places.reviews("ChIJx")
    second = await places.reviews("ChIJx")
    assert first == second
    assert len([c for c in calls if "/v1/places/ChIJx" in c]) == 1
    assert (first.rating, first.count, first.maps_url) == (4.7, 212, "https://maps.google.com/?cid=123")


async def test_reviews_at_most_5():
    result = await _client([]).reviews("ChIJy")
    assert len(result.items) == 5
    assert result.items[0].author == "Guest 0" and result.items[0].text == "Great show 0"


def test_is_google_maps_url():
    assert is_google_maps_url("https://maps.app.goo.gl/AbC")
    assert is_google_maps_url("https://www.google.com/maps/place/X")
    assert is_google_maps_url("https://maps.google.com/?cid=1")
    assert not is_google_maps_url("https://www.google.com/search?q=x")
    assert not is_google_maps_url("https://evil.example.com/maps/place/x")
    assert not is_google_maps_url("javascript:alert(1)")
