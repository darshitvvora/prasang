"""Booking confirmation and the planner check-ins (BookingFollowUpWorkflow)."""
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.auth.models import User
from app.labels import EVENT_TYPE_LABELS
from app.leads.models import Lead
from app.notifications.queue import queue_message
from app.workflows.starter import WorkflowStarter, get_starter

log = logging.getLogger(__name__)
START_GRACE = timedelta(minutes=2)
SWEEP_WINDOW = timedelta(days=30)
REOPEN_FROM = ("new", "contacted", "expired")  # a planner's "booked" converts these; "declined" stays as the artist set it


def _lead_id(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def is_settled(lead: Lead) -> bool:
    return lead.booking_confirmed_at is not None or lead.planner_answer in ("booked", "not_booked")


def confirm(lead: Lead, by: str, now: datetime | None = None) -> bool:
    """Mark the booking confirmed once; returns True when this call confirmed it."""
    if lead.booking_confirmed_at is not None:
        return False
    lead.booking_confirmed_at, lead.booking_confirmed_by = now or datetime.now(UTC), by
    return True


async def booking_state(session: AsyncSession, lead_id: str) -> str:
    lead = await session.get(Lead, _lead_id(lead_id))
    if lead is None:
        return "settled"
    planner = await session.get(User, lead.planner_id)
    if is_settled(lead) or planner is None or planner.deleted_at is not None:
        return "settled"
    return "deciding" if lead.planner_answer == "deciding" else "open"


async def queue_booking_check(session: AsyncSession, lead_id: str, kind: str) -> None:
    lead = await session.get(Lead, _lead_id(lead_id))
    if lead is None:
        return
    artist = await session.get(ArtistProfile, lead.artist_id)
    await queue_message(session, lead.planner_id, kind, str(lead.id),
                        {"artist": artist.stage_name, "event": EVENT_TYPE_LABELS[lead.event_type].lower()})
    await session.commit()


async def start_followup(session: AsyncSession, lead: Lead, starter: WorkflowStarter | None = None) -> bool:
    try:
        await (starter or get_starter()).start_booking_followup(
            str(lead.id), lead.created_at.isoformat(), lead.event_date.isoformat() if lead.event_date else None)
    except Exception:
        log.warning("could not start booking follow-up for lead %s (the sweeper will retry)", lead.id, exc_info=True)
        return False
    lead.followup_started_at = datetime.now(UTC)
    await session.commit()
    return True


async def signal_settled(lead_id: str) -> None:
    try:
        await get_starter().signal_booking_settled(lead_id)
    except Exception:
        log.warning("could not signal booking %s (the workflow re-checks before every message)", lead_id, exc_info=True)


async def retry_booking_followups(session: AsyncSession, starter: WorkflowStarter, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    leads = (await session.execute(select(Lead).where(
        Lead.followup_started_at.is_(None), Lead.created_at > now - SWEEP_WINDOW, Lead.created_at < now - START_GRACE)
        .order_by(Lead.created_at).limit(200))).scalars().all()
    started = 0
    for lead in leads:
        if not await start_followup(session, lead, starter):
            break
        started += 1
    return started
