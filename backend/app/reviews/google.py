"""Google reviews from the artist's Google Business listing (Places API (New)).

Google's terms: show with attribution and don't store review content — only the Place ID is saved; reviews are cached
in this process for at most 24 hours. Without GOOGLE_PLACES_API_KEY nothing is fetched and the profile shows no block.
"""
import logging
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote_plus, urlparse

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)
API = "https://places.googleapis.com/v1"
CACHE_SECONDS = 24 * 3600
MAX_REVIEWS = 5
SHORT_HOSTS = {"maps.app.goo.gl", "goo.gl"}
GOOGLE_HOSTS = {"google.com", "www.google.com", "maps.google.com"}


@dataclass(frozen=True)
class GoogleReview:
    author: str
    rating: int
    relative_time: str
    text: str


@dataclass(frozen=True)
class GoogleReviews:
    rating: float | None
    count: int
    maps_url: str | None
    items: list[GoogleReview]


_cache: dict[str, tuple[float, GoogleReviews]] = {}


def clear_cache() -> None:
    _cache.clear()


def is_google_maps_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if host in SHORT_HOSTS:
        return True
    return host in GOOGLE_HOSTS and (host == "maps.google.com" or parsed.path.startswith("/maps"))


def _place_hint(url: str) -> tuple[str, str] | None:
    """('id', place_id) when the URL carries one, else ('name', text) to search for."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("query_place_id", "place_id"):
        if query.get(key):
            return "id", query[key][0]
    q = (query.get("q") or [""])[0]
    if q.startswith("place_id:"):
        return "id", q.removeprefix("place_id:")
    parts = parsed.path.split("/")
    if "place" in parts and len(parts) > parts.index("place") + 1 and parts[parts.index("place") + 1]:
        return "name", unquote_plus(parts[parts.index("place") + 1])
    if q:
        return "name", q
    return None


class GooglePlaces:
    def __init__(self, api_key: str, http: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self.http = http or httpx.AsyncClient(timeout=5)

    async def resolve_place_id(self, url: str) -> str | None:
        if (urlparse(url).hostname or "").lower() in SHORT_HOSTS:
            res = await self.http.get(url, follow_redirects=False)
            url = res.headers.get("location", url) if res.is_redirect else url
        hint = _place_hint(url)
        if hint is None:
            return None
        kind, value = hint
        if kind == "id":
            return value
        res = await self.http.post(f"{API}/places:searchText", json={"textQuery": value},
                                   headers={"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": "places.id"})
        res.raise_for_status()
        places = res.json().get("places") or []
        return places[0]["id"] if places else None

    async def reviews(self, place_id: str) -> GoogleReviews | None:
        cached = _cache.get(place_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        res = await self.http.get(f"{API}/places/{place_id}", headers={
            "X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": "rating,userRatingCount,reviews,googleMapsUri"})
        res.raise_for_status()
        data = res.json()
        items = [GoogleReview(author=r.get("authorAttribution", {}).get("displayName", "Google user"), rating=int(r.get("rating", 0)),
                              relative_time=r.get("relativePublishTimeDescription", ""),
                              text=(r.get("text") or r.get("originalText") or {}).get("text", ""))
                 for r in (data.get("reviews") or [])[:MAX_REVIEWS]]
        result = GoogleReviews(rating=data.get("rating"), count=data.get("userRatingCount", 0), maps_url=data.get("googleMapsUri"),
                               items=items)
        _cache[place_id] = (time.monotonic() + CACHE_SECONDS, result)
        return result


_places: GooglePlaces | None = None


def get_places() -> GooglePlaces | None:
    global _places
    key = get_settings().google_places_api_key
    if not key:
        return None
    if _places is None or _places.api_key != key:
        _places = GooglePlaces(key)
    return _places


async def resolve(url: str) -> str | None:
    places = get_places()
    if places is None:
        return None
    try:
        return await places.resolve_place_id(url)
    except Exception:
        log.warning("could not resolve Google place for %s", url, exc_info=True)
        return None


async def fetch(place_id: str) -> GoogleReviews | None:
    places = get_places()
    if places is None:
        return None
    try:
        return await places.reviews(place_id)
    except Exception:
        log.warning("could not fetch Google reviews for %s", place_id, exc_info=True)
        return None
