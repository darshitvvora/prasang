"""Billing history: one row per PhonePe payment attempt, recorded once however it reaches us."""
import pytest
from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.subscriptions.models import SubscriptionPayment
from tests.api.phonepe import Gateway, install, order_of, subscribe, webhook
from tests.helpers import ARTIST, PLANNER, seed_demo


@pytest.fixture
def gateway(monkeypatch):
    g = Gateway()
    install(monkeypatch, g)
    return g


async def _count() -> int:
    async with get_sessionmaker()() as s:
        return (await s.execute(select(func.count()).select_from(SubscriptionPayment))).scalar_one()


async def test_failed_then_paid_attempts_newest_first(client, gateway):
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    await webhook(client, order, paid=False, txn="T-declined", ts=1792662600000)
    await webhook(client, order, txn="T-ok", ts=1792662660000)
    items = (await client.get("/api/v1/subscriptions/me/payments", headers=ARTIST)).json()["items"]
    assert [(i["status"], i["receiptUrl"]) for i in items] == [("paid", None), ("failed", None)]
    assert items[0] | {"id": "x"} == {"id": "x", "paidAt": "2026-10-22T09:51:00Z", "tier": "pro", "billingCycle": "monthly",
                                      "amount": 599, "currency": "INR", "status": "paid", "receiptUrl": None}


async def test_same_attempt_from_webhook_and_verify_is_recorded_once(client, gateway):
    await seed_demo()
    sub_id = (await subscribe(client))["subscriptionId"]
    order = await order_of(sub_id)
    await webhook(client, order, txn=f"T-{order[-6:]}")
    gateway.state = "COMPLETED"
    await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={"subscriptionId": sub_id})
    assert await _count() == 1


async def test_payments_endpoint_requires_artist(client, gateway):
    await seed_demo()
    assert (await client.get("/api/v1/subscriptions/me/payments", headers=PLANNER)).status_code == 403
    assert (await client.get("/api/v1/subscriptions/me/payments")).status_code == 401
