"""Payment-link lifecycle: renewals, plan changes, late payments, expiry, missed webhooks and webhook retries."""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.artists.stats import today_ist
from app.db import get_sessionmaker
from app.subscriptions import service
from app.subscriptions.models import Subscription
from tests.api.phonepe import Gateway, arjun, install, messages, order_of, subs, subscribe, webhook
from tests.helpers import ARTIST, NEW, seed_demo


@pytest.fixture
def gateway(monkeypatch):
    g = Gateway()
    install(monkeypatch, g)
    return g


async def _active(tier="pro", cycle="monthly", period_end: date | None = None) -> Subscription:
    """Arjun on a paid period ending `period_end`."""
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()
        artist.subscription_tier, artist.tier_source = tier, "paid"
        sub_id = uuid.uuid4()
        sub = Subscription(id=sub_id, artist_id=artist.id, tier=tier, billing_cycle=cycle, status="active",
                           gateway_subscription_id=service.order_id(sub_id), current_period_end=period_end or today_ist() + timedelta(days=4))
        s.add(sub)
        await s.commit()
        return sub


async def _renewals(gateway) -> int:
    async with get_sessionmaker()() as s:
        return await service.create_due_renewals(s, gateway)


async def test_renewal_link_goes_out_once_five_days_before_the_end(client, gateway):
    await seed_demo()
    current = await _active(period_end=today_ist() + timedelta(days=4))
    assert await _renewals(gateway) == 1
    assert await _renewals(gateway) == 0  # one link per period
    renewal = (await subs())[-1]
    assert (renewal.status, renewal.renews_id, renewal.tier) == ("created", current.id, "pro")
    [(kind, context)] = await messages()
    assert kind == "renewal_due" and context["date"] and context["url"] == renewal.payment_url
    me = (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).json()
    assert me["pendingPayment"]["renewal"] is True and me["subscription"]["id"] == str(current.id)


async def test_no_renewal_link_too_early_or_after_cancel(client, gateway):
    await seed_demo()
    current = await _active(period_end=today_ist() + timedelta(days=10))
    assert await _renewals(gateway) == 0
    async with get_sessionmaker()() as s:
        row = await s.get(Subscription, current.id)
        row.current_period_end, row.cancel_at_period_end = today_ist() + timedelta(days=2), True
        await s.commit()
    assert await _renewals(gateway) == 0


async def test_paying_a_renewal_early_extends_from_the_current_end(client, gateway):
    await seed_demo()
    end = today_ist() + timedelta(days=4)
    current = await _active(period_end=end)
    await _renewals(gateway)
    renewal = (await subs())[-1]
    assert (await webhook(client, renewal.gateway_subscription_id)).status_code == 200
    by_id = {s.id: s for s in await subs()}
    assert by_id[current.id].status == "completed"
    assert (by_id[renewal.id].status, by_id[renewal.id].current_period_end) == ("active", end + timedelta(days=30))
    assert (await arjun()).subscription_tier == "pro"


async def test_upgrade_replaces_a_pending_renewal_which_comes_back_if_the_upgrade_is_not_paid(client, gateway):
    await seed_demo()
    await _active(period_end=today_ist() + timedelta(days=4))
    await _renewals(gateway)
    renewal = (await subs())[-1]
    upgrade_id = (await subscribe(client, "premium"))["subscriptionId"]
    assert renewal.gateway_subscription_id in gateway.cancelled
    async with get_sessionmaker()() as s:
        await service.expire_unpaid(s, upgrade_id, gateway)  # the 24 h link ran out (PhonePe still says ACTIVE)
    assert {str(s.id): s.status for s in await subs()}[upgrade_id] == "expired"
    assert await _renewals(gateway) == 1  # a fresh renewal link for the plan they still have


async def test_plan_change_starts_today_and_replaces_the_old_plan(client, gateway):
    await seed_demo()
    old = await _active(period_end=today_ist() + timedelta(days=20))
    new_id = (await subscribe(client, "premium"))["subscriptionId"]
    await webhook(client, await order_of(new_id), amount=119900)
    by_id = {str(s.id): s for s in await subs()}
    assert by_id[str(old.id)].status == "cancelled"
    assert (by_id[new_id].status, by_id[new_id].current_period_end) == ("active", today_ist() + timedelta(days=30))
    assert (await arjun()).subscription_tier == "premium"


async def test_late_payment_of_a_replaced_link_while_another_plan_is_live_is_flagged(client, gateway):
    await seed_demo()
    stale = (await subscribe(client, "pro"))["subscriptionId"]
    live = (await subscribe(client, "premium"))["subscriptionId"]
    await webhook(client, await order_of(live), amount=119900, txn="T-live")
    await webhook(client, await order_of(stale), txn="T-stale")  # paid in another tab before we cancelled it
    statuses = {str(s.id): s.status for s in await subs()}
    assert statuses == {stale: "cancelled", live: "active"} and (await arjun()).subscription_tier == "premium"
    async with get_sessionmaker()() as s:
        flags = (await s.execute(select(AdminAction.target_id).where(AdminAction.action == "refund_needed"))).scalars().all()
    assert flags == [await order_of(stale)]


async def test_late_payment_of_a_replaced_link_with_no_live_plan_gives_the_plan(client, gateway):
    await seed_demo()
    stale = (await subscribe(client, "pro"))["subscriptionId"]
    await subscribe(client, "premium")  # never paid
    await webhook(client, await order_of(stale))
    assert {str(s.id): s.status for s in await subs()}[stale] == "active"
    assert (await arjun()).subscription_tier == "pro"


async def test_expiry_checks_phonepe_first(client, gateway):
    await seed_demo()
    sub_id = (await subscribe(client))["subscriptionId"]
    gateway.state = "COMPLETED"  # paid, but the webhook never came
    async with get_sessionmaker()() as s:
        await service.expire_unpaid(s, sub_id, gateway)
    assert [s.status for s in await subs()] == ["active"] and gateway.cancelled == []


async def test_sweeper_finds_missed_payments_and_expires_overdue_links(client, gateway):
    await seed_demo()
    paid_id = (await subscribe(client))["subscriptionId"]
    gateway.state = "COMPLETED"
    async with get_sessionmaker()() as s:
        assert await service.reconcile_open_links(s, gateway, min_age=timedelta(0)) == 1
    assert [s.status for s in await subs()] == ["active"]

    gateway.state = "ACTIVE"
    open_id = (await subscribe(client, "premium"))["subscriptionId"]
    async with get_sessionmaker()() as s:
        row = await s.get(Subscription, uuid.UUID(open_id))
        row.pay_by = row.pay_by - timedelta(days=2)
        await s.commit()
        assert await service.expire_overdue_links(s, gateway) == 1
    statuses = {str(s.id): s.status for s in await subs()}
    assert statuses == {paid_id: "active", open_id: "expired"} and gateway.cancelled == [await order_of(open_id)]


async def test_failed_webhook_is_processed_when_redelivered(client, gateway, monkeypatch):
    """The idempotency record must not swallow a delivery that failed mid-processing."""
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    real = service.handle_webhook
    calls = {"n": 0}

    async def flaky(session, event, payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("db blip")
        await real(session, event, payload)

    monkeypatch.setattr(service, "handle_webhook", flaky)
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app
    async with AsyncClient(transport=ASGITransport(app=create_app(), raise_app_exceptions=False), base_url="http://t") as raw:
        assert (await webhook(raw, order)).status_code == 500
    assert (await webhook(client, order)).status_code == 200
    assert [s.status for s in await subs()] == ["active"]
    assert (await webhook(client, order)).json().get("duplicate") is True


async def test_upgrade_to_capped_plan_unlocks_leads_within_new_limit(client, gateway):
    """Basic/free (3) → Pro (15) must reveal locked leads that now fit the cap."""
    await seed_demo()
    async with get_sessionmaker()() as s:
        a = await s.get(ArtistProfile, (await arjun()).id)
        a.subscription_tier, a.tier_source = "free", "free"
        await s.commit()
    assert any(lead["isLocked"] for lead in (await client.get("/api/v1/leads/artist", headers=ARTIST)).json()["items"])
    sub_id = (await subscribe(client, "pro"))["subscriptionId"]
    gateway.state = "COMPLETED"
    await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={"subscriptionId": sub_id})
    assert not any(lead["isLocked"] for lead in (await client.get("/api/v1/leads/artist", headers=ARTIST)).json()["items"])


async def test_trial_on_capped_plan_unlocks_within_limit(client, gateway):
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "T"})
    from tests.api.test_artists import EXAMPLE
    created = (await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"name": "T"})).json()
    await client.patch("/api/v1/artists/me", headers=NEW, json={"isPublished": True})
    from tests.api.test_leads import lead_body
    from tests.helpers import PLANNER
    for i in range(5):
        await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(created["artistId"], eventDate=(date.today() + timedelta(days=50 + i)).isoformat()))
    assert sum(lead["isLocked"] for lead in (await client.get("/api/v1/leads/artist", headers=NEW)).json()["items"]) == 2
    await client.post("/api/v1/subscriptions/trial", headers=NEW, json={"tier": "pro"})
    assert sum(lead["isLocked"] for lead in (await client.get("/api/v1/leads/artist", headers=NEW)).json()["items"]) == 0
