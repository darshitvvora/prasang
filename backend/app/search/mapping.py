"""Index definition for the artists read model. `card` holds the contract ArtistCard verbatim (not indexed)."""
INDEX_BODY = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {"analyzer": {"folded": {"type": "custom", "tokenizer": "standard", "filter": ["lowercase", "asciifolding"]}}},
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "artist_id": {"type": "keyword"},
            "slug": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "folded"},
            "name_suggest": {"type": "search_as_you_type", "analyzer": "folded"},
            "bio": {"type": "text", "analyzer": "folded"},
            "artist_type": {"type": "keyword"},
            "artist_type_label": {"type": "text", "analyzer": "folded"},
            "location_city": {"type": "keyword"},
            "location_area": {"type": "keyword", "fields": {"text": {"type": "text", "analyzer": "folded"}}},
            "per_event_rate_min": {"type": "integer"},
            "per_event_rate_max": {"type": "integer"},
            "average_rating": {"type": "float"},
            "total_reviews": {"type": "integer"},
            "is_verified": {"type": "boolean"},
            "is_featured": {"type": "boolean"},
            "search_boost_score": {"type": "integer"},
            "event_types": {"type": "keyword"},
            "languages": {"type": "keyword"},
            "ready_to_travel": {"type": "boolean"},
            "created_at": {"type": "date"},
            "card": {"type": "object", "enabled": False},
        },
    },
}
