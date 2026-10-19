"""Pure Elasticsearch query builders (unit-tested without a cluster)."""
from dataclasses import dataclass

MAX_SIZE = 50
SORTS = {
    "rating": [{"average_rating": "desc"}, {"total_reviews": "desc"}],
    "price_low": [{"per_event_rate_min": "asc"}],
    "price_high": [{"per_event_rate_max": "desc"}],
    "popular": [{"total_reviews": "desc"}],
    "newest": [{"created_at": "desc"}],
    "relevance": ["_score", {"search_boost_score": "desc"}, {"average_rating": "desc"}],
}


@dataclass
class SearchQuery:
    q: str | None = None
    city: str | None = None
    area: str | None = None
    artist_type: str | None = None
    event_type: str | None = None
    language: str | None = None
    ready_to_travel: bool | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_rating: float | None = None
    verified_only: bool | None = None
    featured_only: bool | None = None
    sort: str = "relevance"
    page: int = 1
    size: int = 20


def _filters(p: SearchQuery) -> list[dict]:
    f: list[dict] = []
    for field, value in (("location_city", p.city), ("location_area", p.area), ("artist_type", p.artist_type),
                         ("event_types", p.event_type), ("languages", p.language)):
        if value:
            f.append({"term": {field: value}})
    if p.ready_to_travel:
        f.append({"term": {"ready_to_travel": True}})
    if p.max_price is not None:
        f.append({"range": {"per_event_rate_min": {"lte": p.max_price}}})
    if p.min_price is not None:
        f.append({"range": {"per_event_rate_max": {"gte": p.min_price}}})
    if p.min_rating:
        f.append({"range": {"average_rating": {"gte": p.min_rating}}})
    if p.verified_only:
        f.append({"term": {"is_verified": True}})
    if p.featured_only:
        f.append({"term": {"is_featured": True}})
    return f


def build_search(p: SearchQuery) -> dict:
    size = max(1, min(p.size, MAX_SIZE))
    must = [{"multi_match": {
        "query": p.q, "fuzziness": "AUTO",
        "fields": ["name^3", "artist_type_label^2", "location_area.text^2", "bio"],
    }}] if p.q else [{"match_all": {}}]
    return {
        "query": {"function_score": {
            "query": {"bool": {"must": must, "filter": _filters(p)}},
            "functions": [
                {"field_value_factor": {"field": "search_boost_score", "modifier": "log1p", "missing": 0}},
                {"filter": {"term": {"is_featured": True}}, "weight": 1.5},
                {"field_value_factor": {"field": "average_rating", "modifier": "log1p", "missing": 0}},
            ],
            "score_mode": "sum", "boost_mode": "sum",
        }},
        "sort": SORTS.get(p.sort, SORTS["relevance"]),
        "from": (max(p.page, 1) - 1) * size,
        "size": size,
        "track_total_hits": True,
        "_source": ["card"],
        "aggs": {"artist_type": {"terms": {"field": "artist_type", "size": 20}},
                 "city": {"terms": {"field": "location_city", "size": 50}}},
    }


def build_similar(artist_id: str, artist_type: str, city: str, size: int) -> dict:
    return {
        "query": {"bool": {
            "filter": [{"term": {"artist_type": artist_type}}],
            "must_not": [{"term": {"artist_id": artist_id}}],
            "should": [{"term": {"location_city": {"value": city, "boost": 2}}}],
        }},
        "sort": ["_score", {"average_rating": "desc"}],
        "size": max(1, min(size, 12)),
        "_source": ["card"],
    }


def build_featured(size: int) -> dict:
    return {"query": {"term": {"is_featured": True}}, "sort": [{"search_boost_score": "desc"}, {"average_rating": "desc"}],
            "size": max(1, min(size, MAX_SIZE)), "_source": ["card"]}


def build_name_suggest(q: str, size: int = 5) -> dict:
    return {"query": {"multi_match": {"query": q, "type": "bool_prefix",
                                      "fields": ["name_suggest", "name_suggest._2gram", "name_suggest._3gram"]}},
            "size": size, "_source": ["card"]}
