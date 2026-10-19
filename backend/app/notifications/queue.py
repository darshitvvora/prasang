"""Outbound message queue: rows are written in the same transaction as the change that causes them, delivered by the
`DeliverMessageWorkflow` once committed, and re-started by the sweeper if Temporal was unreachable."""
import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.artists.models import ArtistProfile
from app.artists.stats import IST
from app.auth.models import User
from app.config import get_settings
from app.notifications.models import QueuedMessage
from app.notifications.notifier import Notifier
from app.notifications.templates import MessageKind, render
from app.subscriptions.models import Subscription, SubscriptionPlan
from app.workflows.starter import WorkflowStarter, get_starter

log = logging.getLogger(__name__)
START_GRACE = timedelta(minutes=2)  # leave the request path time to start it first
_PENDING_KEY = "queued_messages"
_tasks: set[asyncio.Task] = set()


async def queue_message(session: AsyncSession, user_id: str, kind: MessageKind, period_key: str,
                        context: dict | None = None) -> uuid.UUID | None:
    """Queue a message unless this (user, kind, period) was queued before. Delivery starts after the caller commits."""
    stmt = insert(QueuedMessage).values(id=uuid.uuid4(), user_id=user_id, kind=kind, period_key=period_key,
                                        context=context or {}, status="pending", attempts=0, created_at=datetime.now(UTC))
    new_id = (await session.execute(stmt.on_conflict_do_nothing(
        constraint="uq_outbound_messages_user_kind_period").returning(QueuedMessage.id))).scalar_one_or_none()
    if new_id is not None:
        session.sync_session.info.setdefault(_PENDING_KEY, []).append(str(new_id))
    return new_id


async def _start(message_ids: list[str]) -> None:
    for message_id in message_ids:
        try:
            await get_starter().start_message(message_id)
        except Exception:
            log.warning("could not start delivery of message %s (the sweeper will retry)", message_id, exc_info=True)


@event.listens_for(Session, "after_commit")
def _start_after_commit(session: Session) -> None:
    ids = session.info.pop(_PENDING_KEY, None)
    if not ids:
        return
    try:
        task = asyncio.get_running_loop().create_task(_start(ids))
    except RuntimeError:  # no event loop (sync tooling) — the sweeper picks them up
        return
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


@event.listens_for(Session, "after_rollback")
def _forget_after_rollback(session: Session) -> None:
    session.info.pop(_PENDING_KEY, None)


async def _phone(session: AsyncSession, user: User) -> str | None:
    if user.phone:
        return user.phone
    return (await session.execute(select(ArtistProfile.contact_phone).where(ArtistProfile.user_id == user.id))).scalar()


async def deliver(session: AsyncSession, notifier: Notifier, message_id: str) -> str:
    """Send one queued message. Returns 'sent' or 'skipped'; raises if every channel failed (so Temporal retries)."""
    msg = await session.get(QueuedMessage, uuid.UUID(message_id), with_for_update=True)
    if msg is None or msg.status != "pending":
        await session.rollback()
        return "skipped"
    user = await session.get(User, msg.user_id)
    if user is None or user.deleted_at is not None or user.blocked_at is not None:
        msg.status = "failed"
        await session.commit()
        return "skipped"
    rendered = render(msg.kind, user, msg.context, get_settings().public_web_url)
    msg.attempts += 1
    phone, sent, errors = await _phone(session, user), 0, []
    channels = []
    if phone:
        channels.append(("sms", lambda: notifier.send_sms(phone, rendered.sms)))
    if user.email:
        channels.append(("email", lambda: notifier.send_email(user.email, rendered.email_subject, rendered.email_text)))
    for channel, send in channels:
        try:
            await send()
            sent += 1
        except Exception as exc:  # one channel failing must not stop the other
            errors.append(f"{channel}: {exc}")
    if sent == 0 and errors:
        await session.commit()  # keep the attempt count
        raise RuntimeError(f"message {message_id} not delivered: {'; '.join(errors)}")
    msg.status, msg.sent_at = "sent", datetime.now(UTC)
    await session.commit()
    return "sent"


async def retry_pending_messages(session: AsyncSession, starter: WorkflowStarter, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    ids = (await session.execute(select(QueuedMessage.id).where(
        QueuedMessage.status == "pending", QueuedMessage.created_at < now - START_GRACE)
        .order_by(QueuedMessage.created_at).limit(200))).scalars().all()
    started = 0
    for message_id in ids:
        try:
            await starter.start_message(str(message_id))  # workflow id msg-{id} dedupes
        except Exception as exc:
            log.warning("sweep: message %s still not started: %s", message_id, exc)
            break
        started += 1
    return started


def _day(d) -> str:
    return f"{d.day} {d:%b %Y}"


async def queue_due_reminders(session: AsyncSession, now: datetime | None = None) -> int:
    """Trial ending within 48 hours; annual renewal within 7 days. Idempotent through the unique period key."""
    now = now or datetime.now(UTC)
    queued = 0
    trials = (await session.execute(select(ArtistProfile).where(
        ArtistProfile.tier_source == "trial", ArtistProfile.trial_ends_at > now,
        ArtistProfile.trial_ends_at <= now + timedelta(hours=48)))).scalars().all()
    for artist in trials:
        plan = await session.get(SubscriptionPlan, artist.subscription_tier)
        end = artist.trial_ends_at.astimezone(IST).date()
        if await queue_message(session, artist.user_id, "trial_ending", end.isoformat(), {"plan": plan.name, "date": _day(end)}):
            queued += 1
    today = now.astimezone(IST).date()
    renewals = (await session.execute(select(Subscription, ArtistProfile).join(
        ArtistProfile, ArtistProfile.id == Subscription.artist_id).where(
        Subscription.status == "active", Subscription.billing_cycle == "annual", Subscription.cancel_at_period_end.is_(False),
        Subscription.current_period_end >= today, Subscription.current_period_end <= today + timedelta(days=7)))).all()
    for sub, artist in renewals:
        plan = await session.get(SubscriptionPlan, sub.tier)
        key = sub.current_period_end.isoformat()
        if await queue_message(session, artist.user_id, "renewal_reminder", key, {"plan": plan.name, "date": _day(sub.current_period_end)}):
            queued += 1
    await session.commit()
    return queued
