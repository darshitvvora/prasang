from typing import Literal

from pydantic import Field

from app.contract.common import (
    ArtistType,
    ContractModel,
    EventType,
    LeadSource,
    Page,
    Phone,
    SubscriptionTier,
    UtcDatetime,
    YearMonth,
)
from app.contract.leads import ArtistLead
from app.contract.media import Media
from app.contract.subscriptions import PlanUsage


class ArtistCard(ContractModel):
    artist_id: str
    slug: str
    name: str
    artist_type: ArtistType
    profile_image_url: str | None
    bio: str
    location_city: str
    location_area: str
    per_event_rate_min: int
    per_event_rate_max: int
    average_rating: float
    total_reviews: int
    is_verified: bool
    is_featured: bool
    subscription_tier: SubscriptionTier
    instagram_handle: str | None
    youtube_channel: str | None
    facebook_url: str | None
    experience_years: int
    event_types_supported: list[EventType]
    languages_spoken: list[str]
    ready_to_travel: bool


class ArtistCardList(ContractModel):
    items: list[ArtistCard]


class ArtistDetail(ArtistCard):
    media: list[Media]


class CompletenessItem(ContractModel):
    key: Literal["basic_info", "photo", "bio", "media", "instagram", "review"]
    label: str
    done: bool


class ProfileCompleteness(ContractModel):
    percent: int
    items: list[CompletenessItem]


class ArtistProfile(ArtistDetail):
    contact_phone: str
    whatsapp_number: str | None
    is_published: bool
    completeness: ProfileCompleteness


class ArtistProfileInput(ContractModel):
    name: str = Field(min_length=1, max_length=120)
    artist_type: ArtistType
    location_city: str = Field(min_length=1, max_length=80)
    location_area: str = Field(min_length=1, max_length=120)
    bio: str = Field(min_length=1, max_length=2000)
    experience_years: int = Field(ge=0, le=80)
    per_event_rate_min: int = Field(ge=0)
    per_event_rate_max: int = Field(ge=0)
    event_types_supported: list[EventType] = Field(min_length=1)
    languages_spoken: list[str]
    ready_to_travel: bool
    instagram_handle: str | None
    youtube_channel: str | None
    facebook_url: str | None
    contact_phone: Phone
    whatsapp_number: Phone | None


class ArtistProfilePatch(ContractModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    artist_type: ArtistType | None = None
    location_city: str | None = Field(default=None, min_length=1, max_length=80)
    location_area: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, min_length=1, max_length=2000)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    per_event_rate_min: int | None = Field(default=None, ge=0)
    per_event_rate_max: int | None = Field(default=None, ge=0)
    event_types_supported: list[EventType] | None = None
    languages_spoken: list[str] | None = None
    ready_to_travel: bool | None = None
    instagram_handle: str | None = None
    youtube_channel: str | None = None
    facebook_url: str | None = None
    contact_phone: Phone | None = None
    whatsapp_number: Phone | None = None
    is_published: bool | None = None


class Metric(ContractModel):
    value: int
    change_pct: int | None


class RatingMetric(ContractModel):
    value: float
    total_reviews: int


class DashboardMetrics(ContractModel):
    profile_views: Metric
    contact_clicks: Metric
    leads_this_month: Metric
    average_rating: RatingMetric


class LeadSourceStat(ContractModel):
    source: LeadSource
    label: str
    pct: int


class ArtistDashboard(ContractModel):
    greeting_name: str
    is_published: bool
    plan: PlanUsage
    metrics: DashboardMetrics
    recent_leads: list[ArtistLead]
    lead_sources: list[LeadSourceStat]
    completeness: ProfileCompleteness


class Review(ContractModel):
    id: str
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    event_type: EventType
    event_month: YearMonth
    text: str
    created_at: UtcDatetime


ReviewPage = Page[Review]
