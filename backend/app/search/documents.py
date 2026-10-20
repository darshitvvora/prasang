from app.artists.views import to_card
from app.labels import ARTIST_TYPE_LABELS


def artist_document(p) -> dict:
    card = to_card(p)
    return {
        "artist_id": str(p.id), "slug": p.slug, "name": p.stage_name, "name_suggest": p.stage_name, "bio": p.bio,
        "artist_type": p.artist_type, "artist_type_label": ARTIST_TYPE_LABELS[p.artist_type],
        "location_city": p.location_city, "location_area": p.location_area,
        "per_event_rate_min": p.per_event_rate_min, "per_event_rate_max": p.per_event_rate_max,
        "average_rating": float(p.average_rating or 0), "total_reviews": p.total_reviews, "is_verified": card.is_verified,
        "is_featured": p.is_featured, "search_boost_score": p.search_boost_score, "event_types": list(p.event_types_supported),
        "languages": list(p.languages_spoken), "ready_to_travel": p.ready_to_travel, "created_at": p.created_at.isoformat(),
        "card": card.model_dump(by_alias=True, mode="json"),
    }
