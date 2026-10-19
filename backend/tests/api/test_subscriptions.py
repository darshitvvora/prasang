import hashlib
import hmac
import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.subscriptions.models import Subscription
from tests.helpers import ARTIST, NEW, PLANNER, seed_demo


async def _arjun():
    async with get_sessionmaker()() as s:
        return (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == "arjun-malhotra-magic"))).scalar_one()


async def test_plans_match_contract(client):
    await seed_demo()
    plans = (await client.get("/api/v1/subscriptions/plans")).json()["items"]
    example = json.loads((Path(__file__).resolve().parents[3] / "contracts/examples/subscriptions/plans.response.json").read_text())["items"]
    assert plans == example


async def test_trial_once(client):
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Trial Artist"})
    from tests.api.test_artists import EXAMPLE
    await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"name": "Trial Artist"})
    before = (await client.get("/api/v1/subscriptions/me", headers=NEW)).json()
    assert before["plan"]["status"] == "free" and before["plan"]["trialAvailable"] is True and before["subscription"] is None
    res = await client.post("/api/v1/subscriptions/trial", headers=NEW, json={"tier": "pro"})
    assert res.status_code == 200, res.text
    usage = res.json()
    assert (usage["tier"], usage["status"], usage["leadsRemaining"]) == ("pro", "trial", None)
    assert usage["trialEndsAt"] == (date.today() + timedelta(days=7)).isoformat() or usage["trialEndsAt"]
    again = await client.post("/api/v1/subscriptions/trial", headers=NEW, json={"tier": "basic"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "trial_used"


async def test_subscribe_verify_activates_and_unlocks(client):
    await seed_demo()
    res = await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "pro", "billingCycle": "monthly"})
    assert res.status_code == 201, res.text
    checkout = res.json()["checkout"]
    assert checkout["keyId"] == "rzp_test_mock" and checkout["razorpaySubscriptionId"].startswith("sub_mock")
    assert checkout["prefill"]["name"] == "Arjun Malhotra"

    bad = await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={
        "razorpayPaymentId": "pay_1", "razorpaySubscriptionId": checkout["razorpaySubscriptionId"], "razorpaySignature": "forged"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_signature"

    ok = await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={
        "razorpayPaymentId": "pay_1", "razorpaySubscriptionId": checkout["razorpaySubscriptionId"], "razorpaySignature": "mock-signature"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "active" and ok.json()["plan"]["tier"] == "pro"
    arjun = await _arjun()
    assert (arjun.subscription_tier, arjun.tier_source, arjun.search_boost_score) == ("pro", "paid", 25)
    leads = (await client.get("/api/v1/leads/artist", headers=ARTIST)).json()
    assert not any(lead["isLocked"] for lead in leads["items"])

    me = (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).json()
    assert me["subscription"]["status"] == "active" and me["subscription"]["tier"] == "pro"


async def test_retrying_checkout_replaces_unpaid_subscription(client):
    await seed_demo()
    first = (await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "pro", "billingCycle": "monthly"})).json()
    second = await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "premium", "billingCycle": "annual"})
    assert second.status_code == 201
    async with get_sessionmaker()() as s:
        statuses = {str(sub.id): sub.status for sub in (await s.execute(select(Subscription))).scalars()}
    assert statuses[first["subscriptionId"]] == "cancelled" and statuses[second.json()["subscriptionId"]] == "created"


async def test_cancel_at_period_end(client):
    await seed_demo()
    checkout = (await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "pro", "billingCycle": "monthly"})).json()["checkout"]
    await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={
        "razorpayPaymentId": "pay_1", "razorpaySubscriptionId": checkout["razorpaySubscriptionId"], "razorpaySignature": "mock-signature"})
    res = await client.post("/api/v1/subscriptions/cancel", headers=ARTIST)
    assert res.status_code == 200
    body = res.json()
    assert body["subscription"]["cancelAtPeriodEnd"] is True and body["plan"]["status"] == "cancelling"


async def test_webhooks(client, monkeypatch):
    from app.config import get_settings
    await seed_demo()
    monkeypatch.setattr(get_settings(), "razorpay_webhook_secret", "whsec")
    checkout = (await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "basic", "billingCycle": "monthly"})).json()["checkout"]
    sub_id = checkout["razorpaySubscriptionId"]
    end = 1893456000  # 2030-01-01
    payload = {"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": sub_id, "status": "active", "current_end": end}}}}
    body = json.dumps(payload).encode()
    headers = {"X-Razorpay-Signature": hmac.new(b"whsec", body, hashlib.sha256).hexdigest(), "X-Razorpay-Event-Id": "evt_1",
               "Content-Type": "application/json"}

    bad = await client.post("/api/v1/subscriptions/webhook", content=body, headers=headers | {"X-Razorpay-Signature": "forged"})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_signature"
    assert (await client.post("/api/v1/subscriptions/webhook", content=body, headers=headers)).status_code == 200
    assert (await client.post("/api/v1/subscriptions/webhook", content=body, headers=headers)).status_code == 200  # duplicate no-op
    me = (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).json()
    assert me["subscription"]["status"] == "active" and me["subscription"]["currentPeriodEnd"] == "2030-01-01"

    cancelled = {"event": "subscription.cancelled", "payload": {"subscription": {"entity": {"id": sub_id, "status": "cancelled"}}}}
    body = json.dumps(cancelled).encode()
    headers = headers | {"X-Razorpay-Signature": hmac.new(b"whsec", body, hashlib.sha256).hexdigest(), "X-Razorpay-Event-Id": "evt_2"}
    assert (await client.post("/api/v1/subscriptions/webhook", content=body, headers=headers)).status_code == 200
    assert (await _arjun()).subscription_tier == "free"


async def test_planner_cannot_subscribe(client):
    await seed_demo()
    assert (await client.post("/api/v1/subscriptions", headers=PLANNER, json={"tier": "pro", "billingCycle": "monthly"})).status_code == 403


async def test_plan_change_cancels_previous_subscription_at_gateway(client, monkeypatch):
    from app.subscriptions import service
    from app.subscriptions.gateway import FakeGateway

    class Recording(FakeGateway):
        cancelled: list[tuple[str, bool]] = []

        async def cancel_subscription(self, gateway_subscription_id, at_cycle_end):
            self.cancelled.append((gateway_subscription_id, at_cycle_end))

    gateway = Recording()
    monkeypatch.setattr(service, "get_gateway", lambda: gateway, raising=False)
    monkeypatch.setattr("app.subscriptions.router.get_gateway", lambda: gateway)
    await seed_demo()

    async def buy(tier):
        checkout = (await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": tier, "billingCycle": "monthly"})).json()["checkout"]
        await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={
            "razorpayPaymentId": "pay", "razorpaySubscriptionId": checkout["razorpaySubscriptionId"], "razorpaySignature": "mock-signature"})
        return checkout["razorpaySubscriptionId"]

    first = await buy("pro")
    await buy("premium")
    assert (first, False) in gateway.cancelled


async def test_subscription_status_before_artist_profile_is_free_with_trial(client):
    """Contract: before POST /artists, /subscriptions/me returns the Free plan with trialAvailable true."""
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Brand New"})
    res = await client.get("/api/v1/subscriptions/me", headers=NEW)
    assert res.status_code == 200, res.text
    assert res.json()["plan"]["tier"] == "free" and res.json()["plan"]["trialAvailable"] is True and res.json()["subscription"] is None
