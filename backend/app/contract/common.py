"""Shared contract types. Mirrors frontend/src/api/types.ts — keep names identical."""
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from app.schemas import CamelModel


class ContractModel(CamelModel):
    """Every contract model forbids unknown keys, so drift from the TS contract fails loudly."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, extra="forbid")


def _iso_utc(d: datetime) -> str:
    """ISO-8601 UTC with a trailing Z, as the contract requires (naive values are treated as UTC)."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]
Phone = Annotated[str, Field(pattern=r"^[6-9]\d{9}$")]
YearMonth = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]

ArtistType = Literal["magician", "dj", "singer", "comedian", "bubble_artist", "band", "body_double", "anchor", "other"]
EventType = Literal["birthday", "wedding", "pre_wedding", "anniversary", "corporate", "house_party", "other"]
SubscriptionTier = Literal["free", "pro", "premium"]  # "free" is shown as "Basic" (plan name)
PaidTier = Literal["pro", "premium"]
BudgetRange = Literal["5k_10k", "10k_15k", "15k_25k", "25k_50k", "50k_plus"]
LeadStatus = Literal["new", "contacted", "converted", "declined", "expired"]
InquiryStatus = Literal["pending", "responded", "confirmed", "declined"]
LeadSource = Literal["search", "profile", "featured", "direct_link"]
Role = Literal["artist", "planner", "admin"]
MediaKind = Literal["image", "video", "youtube", "instagram", "facebook"]
SocialKind = Literal["youtube", "instagram", "facebook"]
SortOption = Literal["relevance", "rating", "price_low", "price_high", "popular", "newest"]
BillingCycle = Literal["monthly", "annual"]


class ErrorDetail(ContractModel):
    code: str
    message: str
    details: dict = {}


class ErrorBody(ContractModel):
    error: ErrorDetail


class Page[T](ContractModel):
    items: list[T]
    total: int
    page: int
    size: int
