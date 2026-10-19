"""Review fixes Important 3/4: recover work that Temporal never received (sweeper run by the `scheduler` service)."""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select, update

from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.leads.models import Lead
from app.subscriptions.models import Subscription
from app.sweeps import end_overdue_trials, lapse_overdue_subscriptions, retry_lead_notifications
from tests.helpers import seed_demo


class Recording:
    def __init__(self, fail=False):
        self.started, self.fail = [], fail

    async def start_lead_notification(self, lead_id):
        if self.fail:
            raise ConnectionError("temporal down")
        self.started.append(lead_id)


async def test_unnotified_leads_are_retried_once():
    await seed_demo()
    async with get_sessionmaker()() as s:
        await s.execute(update(Lead).values(notification_started_at=datetime.now(UTC)))
        one = (await s.execute(select(Lead).limit(1))).scalar_one()
        one.notification_started_at = None
        one.created_at = datetime.now(UTC) - timedelta(minutes=10)
        await s.commit()
        assert await retry_lead_notifications(s, Recording(fail=True)) == 0  # still down → stays pending
        rec = Recording()
        assert await retry_lead_notifications(s, rec) == 1 and rec.started == [str(one.id)]
        assert await retry_lead_notifications(s, Recording()) == 0


async def test_overdue_trials_end():
    await seed_demo()
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "kabir-mentalist"))).scalar_one()
        artist.subscription_tier, artist.tier_source, artist.trial_used = "pro", "trial", True
        artist.trial_ends_at = datetime.now(UTC) - timedelta(hours=1)
        await s.commit()
        assert await end_overdue_trials(s) == 1
        await s.refresh(artist)
        assert (artist.subscription_tier, artist.tier_source) == ("free", "free")


async def test_overdue_subscriptions_lapse():
    await seed_demo()
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "kabir-mentalist"))).scalar_one()
        artist.subscription_tier, artist.tier_source = "pro", "paid"
        s.add(Subscription(artist_id=artist.id, tier="pro", billing_cycle="monthly", status="active",
                           gateway_subscription_id="sub_old", current_period_end=date.today() - timedelta(days=5)))
        await s.commit()
        assert await lapse_overdue_subscriptions(s) == 1
        await s.refresh(artist)
        assert artist.subscription_tier == "free"
