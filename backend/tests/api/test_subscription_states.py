"""Review fixes: webhook state machine (Critical 1), webhook retries after a failure (Important 1), unlock on capped upgrades (Important 2)."""
import hashlib
import hmac
import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.config import get_settings
from app.db import get_sessionmaker
from app.subscriptions.gateway import FakeGateway
from app.subscriptions.models import Subscription
from tests.helpers import ARTIST, NEW, seed_demo

END_2030 = 1893456000


class RecordingGateway(FakeGateway):
    def __init__(self):
        self.cancelled: list[tuple[str, bool]] = []

    async def cancel_subscription(self, gateway_subscription_id, at_cycle_end):
        self.cancelled.append((gateway_subscription_id, at_cycle_end))


@pytest.fixture
def gateway(monkeypatch):
    g = RecordingGateway()
    monkeypatch.setattr("app.subscriptions.service.get_gateway", lambda: g)
    monkeypatch.setattr("app.subscriptions.router.get_gateway", lambda: g)
    monkeypatch.setattr(get_settings(), "razorpay_webhook_secret", "whsec")
    return g


async def hook(client, event: str, sub_id: str, event_id: str, current_end: int | None = END_2030):
    entity = {"id": sub_id, "status": event.split(".")[1]} | ({"current_end": current_end} if current_end else {})
    body = json.dumps({"event": event, "payload": {"subscription": {"entity": entity}}}).encode()
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    return await client.post("/api/v1/subscriptions/webhook", content=body,
                             headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": event_id, "Content-Type": "application/json"})


async def checkout(client, tier="pro", headers=ARTIST):
    return (await client.post("/api/v1/subscriptions", headers=headers, json={"tier": tier, "billingCycle": "monthly"})).json()["checkout"]["razorpaySubscriptionId"]


async def arjun():
    async with get_sessionmaker()() as s:
        return (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()


async def statuses():
    async with get_sessionmaker()() as s:
        return {sub.gateway_subscription_id: sub.status for sub in (await s.execute(select(Subscription))).scalars()}


async def test_retrying_checkout_cancels_stale_subscription_at_gateway(client, gateway):
    await seed_demo()
    stale = await checkout(client)
    await checkout(client, "premium")
    assert (stale, False) in gateway.cancelled


async def test_late_activation_of_replaced_checkout_gives_the_artist_their_plan(client, gateway):
    """(a) Artist closes checkout, retries, but the first mandate confirms late: they paid, so they must get the tier."""
    await seed_demo()
    stale = await checkout(client, "pro")
    await checkout(client, "premium")  # stale → cancelled locally
    assert (await hook(client, "subscription.activated", stale, "e1")).status_code == 200
    assert (await statuses())[stale] == "active"
    assert (await arjun()).subscription_tier == "pro"


async def test_charge_after_lapse_restores_the_tier(client, gateway):
    """(b) Halted → lapsed to Free → customer fixes card → charged: they must be back on the paid tier."""
    await seed_demo()
    sub = await checkout(client, "pro")
    await hook(client, "subscription.activated", sub, "e1")
    await hook(client, "subscription.halted", sub, "e2", current_end=None)
    from app.subscriptions.service import lapse
    async with get_sessionmaker()() as s:
        row = (await s.execute(select(Subscription).where(Subscription.gateway_subscription_id == sub))).scalar_one()
        await lapse(s, str(row.id))
    assert (await arjun()).subscription_tier == "free"
    await hook(client, "subscription.charged", sub, "e3")
    assert (await statuses())[sub] == "active" and (await arjun()).subscription_tier == "pro"


async def test_late_halt_on_replaced_subscription_is_ignored(client, gateway):
    """(c) A halted event for a subscription already replaced must not create a second live row (500s everywhere)."""
    await seed_demo()
    first = await checkout(client, "pro")
    await hook(client, "subscription.activated", first, "e1")
    second = await checkout(client, "premium")
    await hook(client, "subscription.activated", second, "e2")
    await hook(client, "subscription.halted", first, "e3", current_end=None)
    assert (await statuses())[first] == "cancelled"
    assert (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).status_code == 200
    assert (await client.get("/api/v1/artists/me/dashboard", headers=ARTIST)).status_code == 200


async def test_failed_webhook_is_processed_when_razorpay_retries(client, gateway, monkeypatch):
    """Important 1: the idempotency record must not swallow a delivery that failed mid-processing."""
    await seed_demo()
    sub = await checkout(client, "pro")
    from app.subscriptions import service
    real = service.handle_webhook
    calls = {"n": 0}

    async def flaky(session, event, entity, payment=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("db blip")
        await real(session, event, entity, payment)

    monkeypatch.setattr(service, "handle_webhook", flaky)
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app
    async with AsyncClient(transport=ASGITransport(app=create_app(), raise_app_exceptions=False), base_url="http://t") as raw:
        assert (await hook(raw, "subscription.activated", sub, "evt-retry")).status_code == 500
    assert (await hook(client, "subscription.activated", sub, "evt-retry")).status_code == 200
    assert (await statuses())[sub] == "active"
    again = await hook(client, "subscription.activated", sub, "evt-retry")
    assert again.json().get("duplicate") is True


async def test_upgrade_to_capped_plan_unlocks_leads_within_new_limit(client, gateway):
    """Important 2: Basic/free (3) → Pro (15) must reveal locked leads that now fit the cap."""
    await seed_demo()
    async with get_sessionmaker()() as s:
        a = await arjun()
        a = await s.get(ArtistProfile, a.id)
        a.subscription_tier, a.tier_source = "free", "free"
        await s.commit()
    locked_before = [lead for lead in (await client.get("/api/v1/leads/artist", headers=ARTIST)).json()["items"] if lead["isLocked"]]
    assert locked_before
    sub = await checkout(client, "pro")
    await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={
        "razorpayPaymentId": "p", "razorpaySubscriptionId": sub, "razorpaySignature": "mock-signature"})
    after = (await client.get("/api/v1/leads/artist", headers=ARTIST)).json()["items"]
    assert not any(lead["isLocked"] for lead in after)


async def test_trial_on_capped_plan_unlocks_within_limit(client, gateway):
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "T"})
    from tests.api.test_artists import EXAMPLE
    created = (await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"name": "T", "isPublished": True} if False else EXAMPLE | {"name": "T"})).json()
    await client.patch("/api/v1/artists/me", headers=NEW, json={"isPublished": True})
    from datetime import date, timedelta

    from tests.api.test_leads import lead_body
    from tests.helpers import PLANNER
    for i in range(5):
        await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(created["artistId"], eventDate=(date.today() + timedelta(days=50 + i)).isoformat()))
    assert sum(lead["isLocked"] for lead in (await client.get("/api/v1/leads/artist", headers=NEW)).json()["items"]) == 2
    await client.post("/api/v1/subscriptions/trial", headers=NEW, json={"tier": "pro"})
    assert sum(lead["isLocked"] for lead in (await client.get("/api/v1/leads/artist", headers=NEW)).json()["items"]) == 0
    _ = datetime.now(UTC)
