"""Billing history: one row per gateway payment, receipts link to the gateway's hosted invoice."""
import hashlib
import hmac
import json

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.db import get_sessionmaker
from app.subscriptions.gateway import FakeGateway
from app.subscriptions.models import SubscriptionPayment
from tests.helpers import ARTIST, PLANNER, seed_demo

END_2030 = 1893456000


class InvoiceGateway(FakeGateway):
    async def invoice_url(self, invoice_id):
        return f"https://rzp.io/i/{invoice_id}"


@pytest.fixture
def gateway(monkeypatch):
    g = InvoiceGateway()
    monkeypatch.setattr("app.subscriptions.service.get_gateway", lambda: g)
    monkeypatch.setattr("app.subscriptions.router.get_gateway", lambda: g)
    monkeypatch.setattr(get_settings(), "razorpay_webhook_secret", "whsec")
    return g


def _payment(pid: str, amount=59900, status="captured", invoice="inv_1", sub_id=None, created=1760000000):
    return {"id": pid, "amount": amount, "currency": "INR", "status": status, "invoice_id": invoice,
            "subscription_id": sub_id, "created_at": created}


async def hook(client, event: str, event_id: str, sub_id: str | None, payment: dict | None):
    payload = {}
    if sub_id:
        payload["subscription"] = {"entity": {"id": sub_id, "status": "active", "current_end": END_2030}}
    if payment:
        payload["payment"] = {"entity": payment}
    body = json.dumps({"event": event, "payload": payload}).encode()
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    return await client.post("/api/v1/subscriptions/webhook", content=body, headers={
        "X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": event_id, "Content-Type": "application/json"})


async def _checkout(client) -> str:
    res = await client.post("/api/v1/subscriptions", headers=ARTIST, json={"tier": "pro", "billingCycle": "monthly"})
    return res.json()["checkout"]["razorpaySubscriptionId"]


async def _rows() -> list[SubscriptionPayment]:
    async with get_sessionmaker()() as s:
        return list((await s.execute(select(SubscriptionPayment).order_by(SubscriptionPayment.paid_at))).scalars())


async def test_charged_webhook_records_payment_with_receipt(client, gateway):
    await seed_demo()
    sub = await _checkout(client)
    assert (await hook(client, "subscription.charged", "e1", sub, _payment("pay_1"))).status_code == 200
    [row] = await _rows()
    assert (row.gateway_payment_id, row.amount, row.status, row.receipt_url) == ("pay_1", 59900, "paid", "https://rzp.io/i/inv_1")


async def test_duplicate_charged_webhook_records_once(client, gateway):
    await seed_demo()
    sub = await _checkout(client)
    await hook(client, "subscription.charged", "e1", sub, _payment("pay_1"))
    await hook(client, "subscription.charged", "e2", sub, _payment("pay_1"))
    assert len(await _rows()) == 1


async def test_payment_failed_webhook_records_failed_row(client, gateway):
    await seed_demo()
    sub = await _checkout(client)
    await hook(client, "subscription.activated", "e0", sub, None)
    res = await hook(client, "payment.failed", "e1", None, _payment("pay_bad", status="failed", invoice=None, sub_id=sub))
    assert res.status_code == 200
    [row] = await _rows()
    assert (row.status, row.receipt_url) == ("failed", None)


async def test_verify_records_first_payment(client, gateway):
    await seed_demo()
    sub = await _checkout(client)
    res = await client.post("/api/v1/subscriptions/verify", headers=ARTIST, json={
        "razorpayPaymentId": "pay_first", "razorpaySubscriptionId": sub, "razorpaySignature": "mock-signature"})
    assert res.status_code == 200
    [row] = await _rows()
    assert (row.gateway_payment_id, row.amount, row.status) == ("pay_first", 59900, "paid")


async def test_payments_endpoint_lists_newest_first_for_own_artist_only(client, gateway):
    await seed_demo()
    sub = await _checkout(client)
    await hook(client, "subscription.charged", "e1", sub, _payment("pay_old", created=1750000000, invoice="inv_old"))
    await hook(client, "subscription.charged", "e2", sub, _payment("pay_new", created=1760000000, invoice="inv_new"))
    res = await client.get("/api/v1/subscriptions/me/payments", headers=ARTIST)
    assert res.status_code == 200
    items = res.json()["items"]
    assert [i["receiptUrl"] for i in items] == ["https://rzp.io/i/inv_new", "https://rzp.io/i/inv_old"]
    assert items[0] | {"id": "x", "paidAt": "x"} == {"id": "x", "paidAt": "x", "tier": "pro", "billingCycle": "monthly",
                                                       "amount": 599, "currency": "INR", "status": "paid",
                                                       "receiptUrl": "https://rzp.io/i/inv_new"}
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(func.count()).select_from(SubscriptionPayment))).scalar_one() == 2


async def test_payments_endpoint_requires_artist(client, gateway):
    await seed_demo()
    assert (await client.get("/api/v1/subscriptions/me/payments", headers=PLANNER)).status_code == 403
    assert (await client.get("/api/v1/subscriptions/me/payments")).status_code == 401
