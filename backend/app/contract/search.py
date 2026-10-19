from typing import Literal

from app.contract.artists import ArtistCard
from app.contract.common import ContractModel


class FacetBucket(ContractModel):
    value: str
    count: int


class Facets(ContractModel):
    artist_type: list[FacetBucket]
    city: list[FacetBucket]


class SearchResponse(ContractModel):
    items: list[ArtistCard]
    total: int
    page: int
    size: int
    facets: Facets


class Suggestion(ContractModel):
    type: Literal["artist", "artistType", "area"]
    label: str
    value: str
    slug: str | None


class SuggestionsResponse(ContractModel):
    items: list[Suggestion]
