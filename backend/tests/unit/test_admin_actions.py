"""Admin CLI actions: each changes state, keeps search in sync and leaves an audit row."""
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.admin import actions
from app.admin.cli import build_parser
from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.auth.models import User
from app.db import get_sessionmaker
from app.errors import AppError
from app.reviews.models import Review
from app.subscriptions.gateway import FakeGateway
from app.subscriptions.models import Subscription
from app.sweeps import end_overdue_grants
from tests.helpers import seed_demo

SLUG = "arjun-malhotra-magic"


class RecordingGateway(FakeGateway):
    """The fake reports every link as paid; cancellations are recorded."""

    def __init__(self):
        self.cancelled: list[str] = []

    async def cancel_link(self, order_id):
        self.cancelled.append(order_id)


@pytest.fixture
def gateway(monkeypatch):
    g = RecordingGateway()
    monkeypatch.setattr("app.subscriptions.service.get_gateway", lambda: g)
    monkeypatch.setattr("app.admin.actions.revoke_sessions", _noop)
    return g


async def _noop(user_id: str) -> None:
    return None


async def _artist(s) -> ArtistProfile:
    return (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == SLUG))).scalar_one()


async def _add_sub(s, artist, status="active", gateway_id="sub_live1") -> Subscription:
    sub = Subscription(artist_id=artist.id, tier="pro", billing_cycle="monthly", status=status,
                       gateway_subscription_id=gateway_id, current_period_end=date.today() + timedelta(days=20))
    s.add(sub)
    await s.commit()
    return sub


async def test_block_artist_cancels_live_subscription(gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await _add_sub(s, await _artist(s))
        await _add_sub(s, await _artist(s), status="created", gateway_id="PRS-open")
        await actions.block_user(s, "dev-artist-arjun", actor="test", reason="Fake profile")
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        assert gateway.cancelled == ["PRS-open"]  # the paid period has nothing to cancel; the open link is closed
        assert artist.suspended_at is not None and artist.suspension_reason == "Fake profile"
        assert {sub.status for sub in (await s.execute(select(Subscription))).scalars()} == {"cancelled"}
        assert artist.subscription_tier == "free"
        assert (await s.get(User, "dev-artist-arjun")).blocked_at is not None


async def test_suspend_leaves_billing_running(gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await _add_sub(s, await _artist(s))
        await actions.suspend(s, SLUG, actor="test", reason="check")
    assert gateway.cancelled == []


async def test_grant_plan_sets_tier_and_expires(gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await actions.grant_plan(s, SLUG, "premium", 14, actor="test", reason="Compensation for outage")
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        assert (artist.subscription_tier, artist.tier_source) == ("premium", "grant")
        assert artist.grant_ends_at > datetime.now(UTC) + timedelta(days=13)
        assert await end_overdue_grants(s) == 0
        assert await end_overdue_grants(s, now=datetime.now(UTC) + timedelta(days=15)) == 1
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        assert (artist.subscription_tier, artist.tier_source, artist.grant_ends_at) == ("free", "free", None)


async def test_grant_shows_as_active_plan_until_end(client, gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await actions.grant_plan(s, SLUG, "pro", 10, actor="test", reason="promo")
    body = (await client.get("/api/v1/subscriptions/me", headers={"Authorization": "Bearer mock-artist"})).json()
    assert (body["plan"]["tier"], body["plan"]["status"]) == ("pro", "active")
    assert body["plan"]["periodEnd"] is not None


async def test_grant_refused_with_live_paid(gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await _add_sub(s, await _artist(s))
        with pytest.raises(AppError) as err:
            await actions.grant_plan(s, SLUG, "premium", 7, actor="test", reason="promo")
    assert err.value.code == "grant_conflict"


async def test_hide_review_recalculates_rating(gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        reviews = (await s.execute(select(Review).where(Review.artist_id == artist.id))).scalars().all()
        before = len(reviews)  # demo seed shows a larger display count; recalculation uses real rows
        worst = min(reviews, key=lambda r: r.rating)
        await actions.hide_review(s, str(worst.id), actor="test", reason="Abusive language")
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        assert artist.total_reviews == before - 1
        shown = [r.rating for r in reviews if r.id != worst.id]
        assert artist.average_rating == pytest.approx(round(sum(shown) / len(shown), 2))
        await actions.restore_review(s, str(worst.id), actor="test")
    async with get_sessionmaker()() as s:
        assert (await _artist(s)).total_reviews == before


async def test_sync_subscription_activates_missed_payment(gateway):
    await seed_demo()
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        artist.subscription_tier, artist.tier_source = "free", "free"
        await _add_sub(s, artist, status="created", gateway_id="sub_missed")
        await actions.sync_subscription(s, SLUG, actor="test")
    async with get_sessionmaker()() as s:
        artist = await _artist(s)
        assert (artist.subscription_tier, artist.tier_source) == ("pro", "paid")


@pytest.mark.parametrize("name, args, kwargs", [
    ("make_admin", ["9820098200"], {}),
    ("set_verified", [SLUG, True], {}),
    ("set_featured", [SLUG, True], {}),
    ("suspend", [SLUG], {"reason": "r"}),
    ("restore", [SLUG], {}),
    ("grant_plan", [SLUG, "pro", 3], {"reason": "r"}),
    ("block_user", ["dev-planner-neha"], {"reason": "r"}),
    ("unblock_user", ["dev-planner-neha"], {}),
    ("sync_subscription", [SLUG], {}),
])
async def test_every_action_logs_admin_action(gateway, name, args, kwargs):
    await seed_demo()
    async with get_sessionmaker()() as s:
        if name == "make_admin":
            s.add(User(id="u-admin", full_name="Owner", role="planner", phone="9820098200"))
            await s.commit()
        if name == "sync_subscription":
            await _add_sub(s, await _artist(s))
        await getattr(actions, name)(s, *args, actor="darshit", **kwargs)
    async with get_sessionmaker()() as s:
        row = (await s.execute(select(AdminAction))).scalar_one()
        assert (row.actor, row.action) == ("darshit", name)
        assert row.target_id


async def test_make_admin_by_phone(gateway):
    async with get_sessionmaker()() as s:
        s.add(User(id="u-owner", full_name="Owner", role="planner", phone="9820098200"))
        await s.commit()
        await actions.make_admin(s, "9820098200", actor="test")
    async with get_sessionmaker()() as s:
        assert (await s.get(User, "u-owner")).role == "admin"


@pytest.mark.parametrize("argv", [
    ["suspend", SLUG], ["grant-plan", SLUG, "pro", "--days", "7"], ["hide-review", "abc"], ["block-user", "9820012345"],
])
def test_reason_required(argv):
    with pytest.raises(SystemExit) as exit_:
        build_parser().parse_args(argv)
    assert exit_.value.code == 2


async def test_sync_subscription_backfills_payments(gateway):
    from app.subscriptions.gateway import LinkStatus
    from app.subscriptions.models import SubscriptionPayment

    async def status(order_id):
        return LinkStatus(state="COMPLETED", gateway_order_id="OMO-h", payments=[
            {"id": "pay_hist", "amount": 59900, "status": "paid", "created_at": 1750000000}])

    gateway.link_status = status
    await seed_demo()
    async with get_sessionmaker()() as s:
        await _add_sub(s, await _artist(s))
        await actions.sync_subscription(s, SLUG, actor="test")
    async with get_sessionmaker()() as s:
        row = (await s.execute(select(SubscriptionPayment))).scalar_one()
        assert (row.gateway_payment_id, row.amount, row.status) == ("pay_hist", 59900, "paid")
