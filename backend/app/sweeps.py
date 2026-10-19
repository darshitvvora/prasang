"""Periodic safety nets for work Temporal never received (it was down when the request ran).

Run by the `scheduler` compose service: `python -m app.cli sweep --loop 300`. Every step is idempotent.
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.artists.stats import today_ist
from app.leads.booking import retry_booking_followups
from app.leads.models import Lead
from app.leads.service import expire_leads
from app.notifications.queue import queue_due_reminders, retry_pending_messages
from app.subscriptions.models import Subscription
from app.workflows.starter import WorkflowStarter

log = logging.getLogger(__name__)
NOTIFY_GRACE = timedelta(minutes=2)  # leave the request path time to start it first
LAPSE_GRACE = timedelta(days=3)


async def retry_lead_notifications(session: AsyncSession, starter: WorkflowStarter, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    leads = (await session.execute(select(Lead).where(
        Lead.notification_started_at.is_(None), Lead.created_at < now - NOTIFY_GRACE).order_by(Lead.created_at).limit(200))).scalars().all()
    started = 0
    for lead in leads:
        try:
            await starter.start_lead_notification(str(lead.id))  # workflow id lead-{id} dedupes
        except Exception as exc:
            log.warning("sweep: lead %s still not notified: %s", lead.id, exc)
            break  # Temporal is still down; try again next sweep
        lead.notification_started_at = now
        started += 1
    await session.commit()
    return started


async def end_overdue_trials(session: AsyncSession, now: datetime | None = None) -> int:
    from app.subscriptions.service import end_trial

    now = now or datetime.now(UTC)
    ids = (await session.execute(select(ArtistProfile.id).where(
        ArtistProfile.tier_source == "trial", ArtistProfile.trial_ends_at < now))).scalars().all()
    for artist_id in ids:
        await end_trial(session, artist_id)
    return len(ids)


async def end_overdue_grants(session: AsyncSession, now: datetime | None = None) -> int:
    """Plans granted by an admin end here (5-minute precision is enough)."""
    from app.subscriptions.service import downgrade_to_free

    now = now or datetime.now(UTC)
    artists = (await session.execute(select(ArtistProfile).where(
        ArtistProfile.tier_source == "grant", ArtistProfile.grant_ends_at < now).with_for_update())).scalars().all()
    for artist in artists:
        await downgrade_to_free(session, artist)
    await session.commit()
    return len(artists)


async def lapse_overdue_subscriptions(session: AsyncSession) -> int:
    from app.subscriptions.service import lapse

    cutoff = today_ist() - LAPSE_GRACE
    ids = (await session.execute(select(Subscription.id).where(
        Subscription.status.in_(("active", "halted")), Subscription.current_period_end < cutoff))).scalars().all()
    for sub_id in ids:
        await lapse(session, str(sub_id))
    return len(ids)


async def run_sweeps(session: AsyncSession, starter: WorkflowStarter) -> dict[str, int]:
    result = {
        "lead_notifications": await retry_lead_notifications(session, starter),
        "trials_ended": await end_overdue_trials(session),
        "grants_ended": await end_overdue_grants(session),
        "subscriptions_lapsed": await lapse_overdue_subscriptions(session),
        "leads_expired": await expire_leads(session),
        "reminders_queued": await queue_due_reminders(session),
        "messages_restarted": await retry_pending_messages(session, starter),
        "booking_followups": await retry_booking_followups(session, starter),
    }
    if any(result.values()):
        log.info("sweep: %s", result)
    return result
