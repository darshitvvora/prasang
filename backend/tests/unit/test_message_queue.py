"""Outbound messages: queued in the same transaction as the change, delivered at most once."""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.auth.models import User
from app.db import get_sessionmaker
from app.notifications.models import QueuedMessage
from app.notifications.queue import deliver, queue_due_reminders, queue_message, retry_pending_messages
from app.subscriptions.models import Subscription
from tests.helpers import NEW, seed_demo


class Spy:
    def __init__(self):
        self.sms: list[tuple[str, str]] = []
        self.emails: list[tuple[str, str, str]] = []

    async def send_sms(self, phone, text):
        self.sms.append((phone, text))

    async def send_email(self, to, subject, text):
        self.emails.append((to, subject, text))

    async def send_whatsapp(self, phone, text):
        raise AssertionError("not used")


class RecordingStarter:
    def __init__(self):
        self.started: list[str] = []

    async def start_message(self, message_id: str) -> None:
        self.started.append(message_id)


async def _user(s, uid="u1", phone="9820011111", email="riya@example.com", role="planner") -> User:
    user = User(id=uid, full_name="Riya Shah", role=role, phone=phone, email=email)
    s.add(user)
    await s.commit()
    return user


async def _kinds() -> list[tuple[str, str]]:
    async with get_sessionmaker()() as s:
        return [(m.kind, m.period_key) for m in (await s.execute(select(QueuedMessage).order_by(QueuedMessage.created_at))).scalars()]


async def test_queue_is_at_most_once():
    async with get_sessionmaker()() as s:
        await _user(s)
        first = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
        second = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
    assert first is not None and second is None


async def test_deliver_sends_sms_and_email_and_marks_sent():
    spy = Spy()
    async with get_sessionmaker()() as s:
        await _user(s)
        mid = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
        assert await deliver(s, spy, str(mid)) == "sent"
        msg = await s.get(QueuedMessage, mid)
        assert msg.status == "sent" and msg.sent_at is not None
    assert spy.sms == [("9820011111", "Welcome to Prasang! Find artists for your next event: http://localhost:5173/search")]
    assert [e[0] for e in spy.emails] == ["riya@example.com"]


async def test_deliver_twice_sends_once():
    spy = Spy()
    async with get_sessionmaker()() as s:
        await _user(s)
        mid = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
        await deliver(s, spy, str(mid))
        assert await deliver(s, spy, str(mid)) == "skipped"
    assert len(spy.sms) == 1


async def test_deliver_skips_deleted_or_blocked_user():
    spy = Spy()
    async with get_sessionmaker()() as s:
        user = await _user(s)
        mid = await queue_message(s, "u1", "welcome_planner", "once")
        user.blocked_at = datetime.now(UTC)
        await s.commit()
        assert await deliver(s, spy, str(mid)) == "skipped"
        assert (await s.get(QueuedMessage, mid)).status == "failed"
    assert spy.sms == [] and spy.emails == []


async def test_post_me_queues_welcome_for_role(client):
    res = await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Tanvi Rao"})
    assert res.status_code == 201
    assert await _kinds() == [("welcome_artist", "once")]


async def test_downgrade_queues_plan_ended():
    await seed_demo()
    async with get_sessionmaker()() as s:
        from app.subscriptions.service import downgrade_to_free

        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()
        await downgrade_to_free(s, artist)
        await s.commit()
        msg = (await s.execute(select(QueuedMessage))).scalar_one()
    assert msg.kind == "plan_ended" and msg.user_id == "dev-artist-arjun"
    assert msg.context == {"plan": "Basic"}


async def test_halted_webhook_queues_payment_failed():
    await seed_demo()
    async with get_sessionmaker()() as s:
        from app.subscriptions.service import handle_webhook

        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()
        s.add(Subscription(artist_id=artist.id, tier="basic", billing_cycle="monthly", status="active",
                           gateway_subscription_id="sub_h", current_period_end=date(2026, 11, 1)))
        await s.commit()
        await handle_webhook(s, "subscription.halted", {"id": "sub_h"})
        sub_id = (await s.execute(select(Subscription.id).where(Subscription.gateway_subscription_id == "sub_h"))).scalar_one()
    assert await _kinds() == [("payment_failed", f"{sub_id}-2026-11-01")]


async def test_due_reminders_trial_48h_and_annual_7d_only():
    await seed_demo()
    now = datetime(2026, 10, 19, 6, 0, tzinfo=UTC)
    async with get_sessionmaker()() as s:
        artists = (await s.execute(select(ArtistProfile).order_by(ArtistProfile.slug))).scalars().all()
        trial, soon_trial, annual, monthly = artists[0], artists[1], artists[2], artists[3]
        trial.tier_source, trial.trial_ends_at = "trial", now + timedelta(hours=30)
        soon_trial.tier_source, soon_trial.trial_ends_at = "trial", now + timedelta(days=5)
        s.add(Subscription(artist_id=annual.id, tier="pro", billing_cycle="annual", status="active",
                           gateway_subscription_id="sub_a", current_period_end=date(2026, 10, 24)))
        s.add(Subscription(artist_id=monthly.id, tier="pro", billing_cycle="monthly", status="active",
                           gateway_subscription_id="sub_m", current_period_end=date(2026, 10, 24)))
        await s.commit()
        assert await queue_due_reminders(s, now) == 2
        assert await queue_due_reminders(s, now) == 0
        users = {trial.user_id: "trial_ending", annual.user_id: "renewal_reminder"}
        rows = (await s.execute(select(QueuedMessage))).scalars().all()
        assert {r.user_id: r.kind for r in rows} == users


async def test_sweeper_restarts_pending_messages():
    starter = RecordingStarter()
    async with get_sessionmaker()() as s:
        await _user(s)
        mid = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
        assert await retry_pending_messages(s, starter) == 0  # too fresh: the request path starts it
        assert await retry_pending_messages(s, starter, now=datetime.now(UTC) + timedelta(minutes=5)) == 1
    assert starter.started == [str(mid)]


class Rejecting(Spy):
    async def send_sms(self, phone, text):
        from app.notifications.notifier import NotificationRejected

        raise NotificationRejected("bad number")


class Flaky(Spy):
    async def send_sms(self, phone, text):
        raise RuntimeError("provider down")


async def test_rejected_by_provider_fails_permanently():
    """Final review I2: a number the provider rejects must not be retried forever."""
    async with get_sessionmaker()() as s:
        await _user(s, email=None)
        mid = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
        assert await deliver(s, Rejecting(), str(mid)) == "failed"
        assert (await s.get(QueuedMessage, mid)).status == "failed"


async def test_transient_failures_give_up_after_max_attempts():
    import pytest

    async with get_sessionmaker()() as s:
        await _user(s, email=None)
        mid = await queue_message(s, "u1", "welcome_planner", "once")
        await s.commit()
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await deliver(s, Flaky(), str(mid))  # Temporal retries these
        assert await deliver(s, Flaky(), str(mid)) == "failed"
        msg = await s.get(QueuedMessage, mid)
        assert (msg.status, msg.attempts) == ("failed", 3)
        assert await retry_pending_messages(s, RecordingStarter(), now=datetime.now(UTC) + timedelta(hours=1)) == 0


async def test_payment_failed_sent_once_per_period_and_not_during_checkout():
    """Final review I4: Razorpay retries and declined checkout cards must not each send an SMS."""
    from app.subscriptions.service import handle_webhook

    await seed_demo()
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()
        s.add(Subscription(artist_id=artist.id, tier="basic", billing_cycle="monthly", status="created", gateway_subscription_id="sub_c"))
        s.add(Subscription(artist_id=artist.id, tier="basic", billing_cycle="monthly", status="active",
                           gateway_subscription_id="sub_r", current_period_end=date(2026, 11, 1)))
        await s.commit()
        await handle_webhook(s, "payment.failed", {}, {"id": "pay_c1", "status": "failed", "subscription_id": "sub_c"})
        for pid in ("pay_r1", "pay_r2", "pay_r3"):
            await handle_webhook(s, "payment.failed", {}, {"id": pid, "status": "failed", "subscription_id": "sub_r"})
        await handle_webhook(s, "subscription.halted", {"id": "sub_r"})
    kinds = await _kinds()
    assert [k for k, _ in kinds] == ["payment_failed"]
