import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.admin.models import AdminAction
from app.artists.stats import today_ist
from app.db import get_sessionmaker
from app.subscriptions.gateway import FAKE_LINK_PREFIX
from app.subscriptions.models import SubscriptionPayment
from tests.api.phonepe import Gateway, arjun, install, messages, order_of, subs, subscribe, webhook
from tests.helpers import ARTIST, NEW, PLANNER, seed_demo


@pytest.fixture
def gateway(monkeypatch):
    g = Gateway()
    install(monkeypatch, g)
    return g


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
    assert (usage["tier"], usage["status"], usage["leadsRemaining"]) == ("pro", "trial", 15)  # Pro is capped at 15 now
    assert usage["trialEndsAt"] == (date.today() + timedelta(days=7)).isoformat() or usage["trialEndsAt"]
    again = await client.post("/api/v1/subscriptions/trial", headers=NEW, json={"tier": "pro"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "trial_used"


async def test_subscribe_returns_and_sends_a_payment_link(client, gateway):
    await seed_demo()
    body = await subscribe(client, "pro", "annual")
    order = await order_of(body["subscriptionId"])
    assert body["payment"]["url"] == f"{FAKE_LINK_PREFIX}{order}" and body["payment"]["amount"] == 5988
    [(created_order, paise, customer)] = gateway.created
    assert (created_order, paise, customer["phone"]) == (order, 598800, "9820011001")
    [(kind, context)] = await messages()
    assert kind == "payment_link" and context["url"] == body["payment"]["url"] and context["amount"] == "₹5,988"
    pending = (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).json()["pendingPayment"]
    assert pending == {"subscriptionId": body["subscriptionId"], "tier": "pro", "billingCycle": "annual", "renewal": False,
                       "payment": body["payment"]}


async def test_verify_waits_for_phonepe_then_activates_and_unlocks(client, gateway):
    await seed_demo()
    sub_id = (await subscribe(client))["subscriptionId"]
    waiting = await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={"subscriptionId": sub_id})
    assert waiting.status_code == 200 and waiting.json()["status"] == "pending_activation"

    gateway.state = "COMPLETED"
    ok = await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={"subscriptionId": sub_id})
    assert ok.json()["status"] == "active" and ok.json()["plan"]["tier"] == "pro"
    artist = await arjun()
    assert (artist.subscription_tier, artist.tier_source, artist.search_boost_score) == ("pro", "paid", 10)
    leads = (await client.get("/api/v1/leads/artist", headers=ARTIST)).json()
    assert not any(lead["isLocked"] for lead in leads["items"])
    me = (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).json()
    assert me["subscription"]["status"] == "active" and me["pendingPayment"] is None
    assert me["subscription"]["currentPeriodEnd"] == (today_ist() + timedelta(days=30)).isoformat()
    assert [k for k, _ in await messages()] == ["payment_link", "payment_received"]


async def test_verify_unknown_or_foreign_subscription(client, gateway):
    await seed_demo()
    for bad in ("not-a-uuid", "6f1c2a9e-3b4d-4c5e-8f70-1a2b3c4d5e6f"):
        res = await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={"subscriptionId": bad})
        assert res.status_code == 404 and res.json()["error"]["code"] == "subscription_not_found"


async def test_retrying_replaces_and_cancels_the_unpaid_link(client, gateway):
    await seed_demo()
    first = (await subscribe(client, "pro"))["subscriptionId"]
    second = (await subscribe(client, "premium", "annual"))["subscriptionId"]
    statuses = {str(s.id): s.status for s in await subs()}
    assert statuses == {first: "cancelled", second: "created"}
    assert gateway.cancelled == [await order_of(first)]


async def test_phonepe_down_returns_502_and_keeps_nothing(client, gateway):
    await seed_demo()
    gateway.fail_create = True
    res = await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "pro", "billingCycle": "monthly"})
    assert res.status_code == 502 and res.json()["error"]["code"] == "payments_unavailable"
    assert await subs() == [] and await messages() == []


async def test_webhook_activates_once_and_rejects_bad_auth(client, gateway):
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    bad = await webhook(client, order, auth="0" * 64)
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_signature"
    assert (await webhook(client, order)).status_code == 200
    assert (await webhook(client, order)).json().get("duplicate") is True
    me = (await client.get("/api/v1/subscriptions/me", headers=ARTIST)).json()
    assert me["subscription"]["status"] == "active" and me["plan"]["tier"] == "pro"
    async with get_sessionmaker()() as s:
        [row] = (await s.execute(select(SubscriptionPayment))).scalars().all()
    assert (row.gateway_payment_id, row.amount, row.status, row.gateway_invoice_id) == ("T1", 59900, "paid", "OMO1")
    assert [k for k, _ in await messages()].count("payment_received") == 1


async def test_failed_attempt_is_recorded_without_activating(client, gateway):
    await seed_demo()
    sub_id = (await subscribe(client))["subscriptionId"]
    assert (await webhook(client, await order_of(sub_id), paid=False, txn="T-bad")).status_code == 200
    [sub] = await subs()
    assert sub.status == "created"
    payments = (await client.get("/api/v1/subscriptions/me/payments", headers=ARTIST)).json()["items"]
    assert [(p["status"], p["amount"]) for p in payments] == [("failed", 599)]


async def test_underpaid_link_is_flagged_not_activated(client, gateway):
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    await webhook(client, order, amount=100)
    [sub] = await subs()
    assert sub.status == "created"
    async with get_sessionmaker()() as s:
        [flag] = (await s.execute(select(AdminAction).where(AdminAction.action == "refund_needed"))).scalars().all()
    assert flag.target_id == order


async def test_cancel_stops_renewal_and_closes_an_open_renewal_link(client, gateway):
    await seed_demo()
    gateway.state = "COMPLETED"
    sub_id = (await subscribe(client))["subscriptionId"]
    await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={"subscriptionId": sub_id})
    gateway.state = "ACTIVE"
    from app.subscriptions.models import Subscription
    async with get_sessionmaker()() as s:
        row = await s.get(Subscription, __import__("uuid").UUID(sub_id))
        row.current_period_end = today_ist() + timedelta(days=2)
        await s.commit()
        from app.subscriptions.service import create_due_renewals
        assert await create_due_renewals(s, gateway) == 1
    renewal = (await subs())[-1]
    res = await client.post("/api/v1/subscriptions/cancel", headers=ARTIST)
    assert res.status_code == 200
    body = res.json()
    assert body["subscription"]["cancelAtPeriodEnd"] is True and body["plan"]["status"] == "cancelling"
    assert body["pendingPayment"] is None and renewal.gateway_subscription_id in gateway.cancelled


async def test_planner_cannot_subscribe(client, gateway):
    await seed_demo()
    assert (await client.post("/api/v1/subscriptions", headers=PLANNER, json={"tier": "pro", "billingCycle": "monthly"})).status_code == 403


async def test_subscription_status_before_artist_profile_is_free_with_trial(client):
    """Contract: before POST /artists, /subscriptions/me returns the Free plan with trialAvailable true."""
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Brand New"})
    res = await client.get("/api/v1/subscriptions/me", headers=NEW)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["plan"]["tier"] == "free" and body["plan"]["trialAvailable"] is True
    assert body["subscription"] is None and body["pendingPayment"] is None
