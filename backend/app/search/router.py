"""Read side: every listing/search the UI shows comes from Elasticsearch."""
from functools import lru_cache

from elasticsearch import AsyncElasticsearch
from elasticsearch import ConnectionError as EsConnectionError
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.service import get_public
from app.contract import (
    ArtistCard,
    ArtistCardList,
    ArtistType,
    EventType,
    FacetBucket,
    Facets,
    SearchResponse,
    SortOption,
    Suggestion,
    SuggestionsResponse,
)
from app.db import get_session
from app.errors import AppError
from app.labels import ARTIST_TYPE_LABELS
from app.locations.models import Locality
from app.search.es import alias, get_es
from app.search.query import SearchQuery, build_featured, build_name_suggest, build_search, build_similar

router = APIRouter(tags=["search"])
JSON = {"response_model_by_alias": True}


@lru_cache
def shared_es() -> AsyncElasticsearch:
    return get_es()


async def _search(body: dict) -> dict:
    try:
        return (await shared_es().search(index=alias(), body=body)).body
    except EsConnectionError as exc:
        raise AppError(503, "search_unavailable", "Search is temporarily unavailable. Please try again shortly.") from exc


def _cards(res: dict) -> list[ArtistCard]:
    return [ArtistCard.model_validate(hit["_source"]["card"]) for hit in res["hits"]["hits"]]


@router.get("/search/artists", response_model=SearchResponse, **JSON)
async def search_artists(
    q: str | None = Query(None, max_length=100), city: str | None = None, area: str | None = None,
    artist_type: ArtistType | None = Query(None, alias="artistType"), event_type: EventType | None = Query(None, alias="eventType"),
    language: str | None = None, ready_to_travel: bool | None = Query(None, alias="readyToTravel"),
    min_price: int | None = Query(None, alias="minPrice", ge=0), max_price: int | None = Query(None, alias="maxPrice", ge=0),
    min_rating: float | None = Query(None, alias="minRating", ge=0, le=5), verified_only: bool | None = Query(None, alias="verifiedOnly"),
    featured_only: bool | None = Query(None, alias="featuredOnly"), sort: SortOption = "relevance",
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50),
):
    params = SearchQuery(q=q, city=city, area=area, artist_type=artist_type, event_type=event_type, language=language,
                         ready_to_travel=ready_to_travel, min_price=min_price, max_price=max_price, min_rating=min_rating,
                         verified_only=verified_only, featured_only=featured_only, sort=sort, page=page, size=size)
    res = await _search(build_search(params))
    aggs = res.get("aggregations", {})
    facets = Facets(
        artist_type=[FacetBucket(value=b["key"], count=b["doc_count"]) for b in aggs.get("artist_type", {}).get("buckets", [])],
        city=[FacetBucket(value=b["key"], count=b["doc_count"]) for b in aggs.get("city", {}).get("buckets", [])],
    )
    return SearchResponse(items=_cards(res), total=res["hits"]["total"]["value"], page=page, size=size, facets=facets)


@router.get("/search/suggestions", response_model=SuggestionsResponse, **JSON)
async def suggestions(q: str = Query(..., min_length=1, max_length=60), db: AsyncSession = Depends(get_session)):
    needle = q.strip().lower()
    items = [Suggestion(type="artistType", label=label, value=key, slug=None)
             for key, label in ARTIST_TYPE_LABELS.items() if label.lower().startswith(needle) or key.startswith(needle)]
    res = await _search(build_name_suggest(q, size=5))
    items += [Suggestion(type="artist", label=c.name, value=c.name, slug=c.slug) for c in _cards(res)]
    areas = (await db.execute(select(Locality).where(Locality.area.ilike(f"{needle}%")).order_by(Locality.sort_order).limit(3))).scalars()
    items += [Suggestion(type="area", label=f"{a.area}, {a.city}", value=a.area, slug=None) for a in areas]
    return SuggestionsResponse(items=items[:8])


@router.get("/artists/featured", response_model=ArtistCardList, **JSON)
async def featured(size: int = Query(12, ge=1, le=50)):
    return ArtistCardList(items=_cards(await _search(build_featured(size))))


@router.get("/artists/{slug}/similar", response_model=ArtistCardList, **JSON)
async def similar(slug: str, size: int = Query(3, ge=1, le=12), db: AsyncSession = Depends(get_session)):
    artist = await get_public(db, slug)
    res = await _search(build_similar(str(artist.id), artist.artist_type, artist.location_city, size))
    return ArtistCardList(items=_cards(res))
