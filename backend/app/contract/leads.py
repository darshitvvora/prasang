from datetime import date

from pydantic import Field

from app.contract.common import (
    ArtistType,
    BudgetRange,
    ContractModel,
    EventType,
    InquiryStatus,
    LeadSource,
    LeadStatus,
    Phone,
    UtcDatetime,
)
from app.contract.subscriptions import PlanUsage


class CreateLeadRequest(ContractModel):
    artist_id: str
    planner_name: str = Field(min_length=1, max_length=120)
    planner_phone: Phone
    planner_email: str | None
    event_type: EventType
    event_date: date | None
    event_city: str | None
    budget_range: BudgetRange
    notes: str | None = Field(default=None, max_length=1000)
    source: LeadSource


class LeadArtistContact(ContractModel):
    name: str
    contact_phone: str
    whatsapp_number: str | None
    instagram_handle: str | None


class CreateLeadResponse(ContractModel):
    lead_id: str
    artist: LeadArtistContact


class ArtistLead(ContractModel):
    id: str
    planner_name: str
    planner_phone: str | None
    planner_email: str | None
    event_type: EventType
    event_title: str
    event_date: date | None
    event_city: str | None
    budget_min: int
    budget_max: int | None
    notes: str | None
    status: LeadStatus
    is_locked: bool
    created_at: UtcDatetime


class LeadCounts(ContractModel):
    all: int
    new: int
    contacted: int
    converted: int
    declined: int
    expired: int


class ArtistLeadsResponse(ContractModel):
    items: list[ArtistLead]
    total: int
    page: int
    size: int
    counts: LeadCounts
    plan: PlanUsage


class UpdateLeadRequest(ContractModel):
    status: LeadStatus


class InquiryArtist(ContractModel):
    artist_id: str
    slug: str
    name: str
    artist_type: ArtistType
    profile_image_url: str | None


class PlannerInquiry(ContractModel):
    id: str
    artist: InquiryArtist
    event_type: EventType
    event_title: str
    event_date: date | None
    days_to_event: int | None
    budget_min: int
    budget_max: int | None
    notes: str | None
    status: InquiryStatus
    contacted_at: UtcDatetime


class InquiryCounts(ContractModel):
    all: int
    pending: int
    responded: int
    confirmed: int
    declined: int


class UpcomingEvent(ContractModel):
    inquiry_id: str
    event_title: str
    artist_name: str
    event_date: date
    days_to_event: int


class InquirySummary(ContractModel):
    artists_contacted: int
    responses_received: int
    confirmed_bookings: int
    upcoming: UpcomingEvent | None


class PlannerInquiriesResponse(ContractModel):
    items: list[PlannerInquiry]
    total: int
    page: int
    size: int
    counts: InquiryCounts
    summary: InquirySummary
