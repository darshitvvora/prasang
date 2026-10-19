"""Leads: planner contacts an artist (quota-locked when over the monthly cap), artist pipeline, planner inquiries."""
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.artists.service import get_own, usage_for
from app.artists.stats import today_ist
from app.auth.models import User
from app.contract import (
    ArtistLeadsResponse,
    CreateLeadRequest,
    InquiryArtist,
    InquiryCounts,
    InquirySummary,
    LeadCounts,
    PlannerInquiriesResponse,
    PlannerInquiry,
    UpcomingEvent,
)
from app.errors import AppError, conflict, not_found
from app.labels import EVENT_TYPE_LABELS
from app.leads.budgets import BUDGETS
from app.leads.models import Lead
from app.leads.usage import month_bounds_ist
from app.leads.views import to_artist_lead
from app.subscriptions.models import SubscriptionPlan

DAILY_PLANNER_LIMIT = 10
TRANSITIONS = {"new": {"contacted", "converted", "declined"}, "contacted": {"converted", "declined"}}
TO_INQUIRY = {"new": "pending", "contacted": "responded", "converted": "confirmed", "declined": "declined", "expired": "declined"}
FROM_INQUIRY = {"pending": ["new"], "responded": ["contacted"], "confirmed": ["converted"], "declined": ["declined", "expired"]}


def _uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def create_lead(session: AsyncSession, planner: User, data: CreateLeadRequest, now: datetime | None = None) -> tuple[Lead, bool]:
    """Returns (lead, created). The artist row is locked so concurrent leads see a consistent monthly count."""
    now = now or datetime.now(UTC)
    artist_id = _uuid(data.artist_id)
    artist = None
    if artist_id is not None:
        artist = (await session.execute(select(ArtistProfile).where(
            ArtistProfile.id == artist_id, ArtistProfile.is_published.is_(True)).with_for_update())).scalar_one_or_none()
    if artist is None:
        raise not_found("artist_not_found", "No artist found for this link")
    if artist.suspended_at is not None:
        await session.rollback()
        raise conflict("artist_suspended", "This artist isn't taking enquiries on Prasang right now")

    existing = (await session.execute(select(Lead).where(
        Lead.artist_id == artist.id, Lead.planner_id == planner.id,
        Lead.event_date.is_(None) if data.event_date is None else Lead.event_date == data.event_date))).scalars().first()
    if existing is not None:
        await session.commit()  # release the row lock; keeps loaded attributes (expire_on_commit=False)
        return existing, False

    recent = (await session.execute(select(func.count()).select_from(Lead).where(
        Lead.planner_id == planner.id, Lead.created_at >= now - timedelta(days=1)))).scalar_one()
    if recent >= DAILY_PLANNER_LIMIT:
        raise AppError(429, "lead_rate_limited", "You have contacted many artists today. Please try again tomorrow.",
                       {"retryAfterSeconds": 86400})

    plan = await session.get(SubscriptionPlan, artist.subscription_tier)
    start, end = month_bounds_ist(now)
    this_month = (await session.execute(select(func.count()).select_from(Lead).where(
        Lead.artist_id == artist.id, Lead.created_at >= start, Lead.created_at < end))).scalar_one()
    locked = plan.lead_limit_monthly >= 0 and this_month >= plan.lead_limit_monthly

    low, high = BUDGETS[data.budget_range]
    lead = Lead(artist_id=artist.id, planner_id=planner.id, planner_name=data.planner_name.strip(), planner_phone=data.planner_phone,
                planner_email=data.planner_email, event_type=data.event_type, event_date=data.event_date, event_city=data.event_city,
                budget_range=data.budget_range, budget_min=low, budget_max=high, notes=data.notes, source=data.source,
                status="new", is_locked=locked, created_at=now)
    session.add(lead)
    artist.total_leads += 1
    await session.commit()
    return lead, True


async def artist_contact(session: AsyncSession, lead: Lead) -> ArtistProfile:
    return await session.get(ArtistProfile, lead.artist_id)


async def artist_leads(session: AsyncSession, user: User, status: str | None, page: int, size: int) -> ArtistLeadsResponse:
    artist = await get_own(session, user)
    base = Lead.artist_id == artist.id
    by_status = dict((await session.execute(select(Lead.status, func.count()).where(base).group_by(Lead.status))).all())
    statuses = ("new", "contacted", "converted", "declined", "expired")
    counts = LeadCounts(all=sum(by_status.values()), **{s: by_status.get(s, 0) for s in statuses})
    where = and_(base, Lead.status == status) if status else base
    total = (await session.execute(select(func.count()).select_from(Lead).where(where))).scalar_one()
    query = select(Lead).where(where).order_by(Lead.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await session.execute(query)).scalars()
    return ArtistLeadsResponse(items=[to_artist_lead(r) for r in rows], total=total, page=page, size=size, counts=counts,
                               plan=await usage_for(session, artist, datetime.now(UTC)))


async def update_status(session: AsyncSession, user: User, lead_id: str, status: str):
    artist = await get_own(session, user)
    lid = _uuid(lead_id)
    lead = await session.get(Lead, lid) if lid else None
    if lead is None or lead.artist_id != artist.id:
        raise not_found("lead_not_found", "That lead doesn't exist")
    if status not in TRANSITIONS.get(lead.status, set()):
        raise conflict("invalid_transition", f"A {lead.status} lead can't be marked {status}")
    lead.status = status
    await session.commit()
    return to_artist_lead(lead)


async def planner_inquiries(session: AsyncSession, user: User, status: str | None, page: int, size: int,
                            today: date | None = None) -> PlannerInquiriesResponse:
    today = today or today_ist()
    base = Lead.planner_id == user.id
    by_status = dict((await session.execute(select(Lead.status, func.count()).where(base).group_by(Lead.status))).all())
    inquiry_counts = {k: sum(by_status.get(s, 0) for s in v) for k, v in FROM_INQUIRY.items()}
    where = and_(base, Lead.status.in_(FROM_INQUIRY[status])) if status else base
    total = (await session.execute(select(func.count()).select_from(Lead).where(where))).scalar_one()
    rows = (await session.execute(select(Lead, ArtistProfile).join(ArtistProfile, ArtistProfile.id == Lead.artist_id).where(where)
                                  .order_by(Lead.created_at.desc()).offset((page - 1) * size).limit(size))).all()
    items = [PlannerInquiry(
        id=str(lead.id), artist=InquiryArtist(artist_id=str(a.id), slug=a.slug, name=a.stage_name, artist_type=a.artist_type,
                                              profile_image_url=a.profile_image_url),
        event_type=lead.event_type, event_title=EVENT_TYPE_LABELS[lead.event_type], event_date=lead.event_date,
        days_to_event=(lead.event_date - today).days if lead.event_date else None, budget_min=lead.budget_min,
        budget_max=lead.budget_max, notes=lead.notes, status=TO_INQUIRY[lead.status], contacted_at=lead.created_at,
    ) for lead, a in rows]

    artists_contacted = (await session.execute(select(func.count(func.distinct(Lead.artist_id))).where(base))).scalar_one()
    upcoming_row = (await session.execute(select(Lead, ArtistProfile).join(ArtistProfile, ArtistProfile.id == Lead.artist_id).where(
        base, Lead.event_date >= today, Lead.status.not_in(("declined", "expired"))).order_by(Lead.event_date).limit(1))).first()
    upcoming = None
    if upcoming_row:
        lead, a = upcoming_row
        upcoming = UpcomingEvent(inquiry_id=str(lead.id), event_title=EVENT_TYPE_LABELS[lead.event_type], artist_name=a.stage_name,
                                 event_date=lead.event_date, days_to_event=(lead.event_date - today).days)
    summary = InquirySummary(artists_contacted=artists_contacted,
                             responses_received=inquiry_counts["responded"] + inquiry_counts["confirmed"],
                             confirmed_bookings=inquiry_counts["confirmed"], upcoming=upcoming)
    return PlannerInquiriesResponse(items=items, total=total, page=page, size=size,
                                    counts=InquiryCounts(all=sum(by_status.values()), **inquiry_counts), summary=summary)


async def unlock_month(session: AsyncSession, artist_id, now: datetime, limit: int = -1) -> int:
    """After a tier change, reveal this month's locked leads that fit the new monthly limit (oldest first)."""
    start, end = month_bounds_ist(now)
    month = and_(Lead.artist_id == artist_id, Lead.created_at >= start, Lead.created_at < end)
    if limit < 0:
        res = await session.execute(update(Lead).where(month, Lead.is_locked.is_(True)).values(is_locked=False))
        return res.rowcount or 0
    unlocked = (await session.execute(select(func.count()).select_from(Lead).where(month, Lead.is_locked.is_(False)))).scalar_one()
    allowance = limit - unlocked
    if allowance <= 0:
        return 0
    oldest_locked = select(Lead.id).where(month, Lead.is_locked.is_(True)).order_by(Lead.created_at).limit(allowance)
    ids = (await session.execute(oldest_locked)).scalars().all()
    if ids:
        await session.execute(update(Lead).where(Lead.id.in_(ids)).values(is_locked=False))
    return len(ids)


async def expire_leads(session: AsyncSession, today: date | None = None) -> int:
    res = await session.execute(update(Lead).where(Lead.status == "new", Lead.event_date < (today or today_ist())).values(status="expired"))
    await session.commit()
    return res.rowcount or 0
