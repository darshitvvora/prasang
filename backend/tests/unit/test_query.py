from app.search.query import SearchQuery, build_search


def _filters(body):
    return body["query"]["function_score"]["query"]["bool"]["filter"]


def test_filters_map_to_terms_and_ranges():
    body = build_search(SearchQuery(city="Pune", area="Wakad", artist_type="dj", event_type="wedding", language="Hindi",
                                    ready_to_travel=True, min_rating=4.5, verified_only=True, featured_only=True))
    f = _filters(body)
    assert {"term": {"location_city": "Pune"}} in f
    assert {"term": {"location_area": "Wakad"}} in f
    assert {"term": {"artist_type": "dj"}} in f
    assert {"term": {"event_types": "wedding"}} in f
    assert {"term": {"languages": "Hindi"}} in f
    assert {"term": {"ready_to_travel": True}} in f
    assert {"range": {"average_rating": {"gte": 4.5}}} in f
    assert {"term": {"is_verified": True}} in f
    assert {"term": {"is_featured": True}} in f


def test_price_filter_is_range_overlap():
    f = _filters(build_search(SearchQuery(min_price=10000, max_price=20000)))
    assert {"range": {"per_event_rate_min": {"lte": 20000}}} in f
    assert {"range": {"per_event_rate_max": {"gte": 10000}}} in f


def test_text_query_is_fuzzy_multi_match():
    must = build_search(SearchQuery(q="magic"))["query"]["function_score"]["query"]["bool"]["must"]
    assert must[0]["multi_match"]["query"] == "magic"
    assert must[0]["multi_match"]["fuzziness"] == "AUTO"


def test_sorts_and_paging():
    assert build_search(SearchQuery(sort="price_low"))["sort"][0] == {"per_event_rate_min": "asc"}
    assert build_search(SearchQuery(sort="price_high"))["sort"][0] == {"per_event_rate_max": "desc"}
    assert build_search(SearchQuery(sort="rating"))["sort"][0] == {"average_rating": "desc"}
    body = build_search(SearchQuery(page=3, size=20))
    assert (body["from"], body["size"]) == (40, 20)
    assert build_search(SearchQuery(size=500))["size"] == 50
