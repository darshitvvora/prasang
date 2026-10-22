"""Test doubles for PhonePe payment links: a scriptable gateway and signed webhook deliveries."""
import hashlib
import json
import time

from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.config import get_settings
from app.db import get_sessionmaker
from app.notifications.models import QueuedMessage
from app.subscriptions.gateway import FAKE_LINK_PREFIX, LinkStatus, PaymentLink
from app.subscriptions.models import Subscription
from tests.helpers import ARTIST

WEBHOOK_AUTH = hashlib.sha256(b"prasang:hook-secret").hexdigest()
ARJUN = "arjun-malhotra-magic"


class Gateway:
    """Behaves like PhonePe (not a FakeGateway, so the sweeper's status checks run). `state` is what status calls return."""

    def __init__(self, state: str = "ACTIVE"):
        self.state, self.amount = state, None
        self.created: list[tuple[str, int, dict]] = []
        self.cancelled: list[str] = []
        self.fail_create = self.fail_cancel = False

    async def create_link(self, order_id, amount_paise, description, **customer):
        if self.fail_create:
            raise RuntimeError("phonepe down")
        self.created.append((order_id, amount_paise, customer))
        return PaymentLink(url=f"{FAKE_LINK_PREFIX}{order_id}", expires_at=customer["expires_at"], gateway_order_id=f"OMO-{order_id[-6:]}")

    async def cancel_link(self, order_id):
        if self.fail_cancel:
            raise RuntimeError("phonepe down")
        self.cancelled.append(order_id)

    async def link_status(self, order_id):
        payments = [{"id": f"T-{order_id[-6:]}", "amount": self.amount, "status": "paid", "created_at": int(time.time())}] \
            if self.state == "COMPLETED" else []
        return LinkStatus(state=self.state, gateway_order_id=f"OMO-{order_id[-6:]}", payments=payments)

    def verify_webhook(self, authorization):
        from app.subscriptions.gateway import webhook_authorized

        return webhook_authorized(authorization)


def install(monkeypatch, gateway) -> None:
    for target in ("app.subscriptions.service.get_gateway", "app.subscriptions.router.get_gateway",
                   "app.subscriptions.gateway.get_gateway"):
        monkeypatch.setattr(target, lambda: gateway)
    monkeypatch.setattr(get_settings(), "phonepe_webhook_username", "prasang")
    monkeypatch.setattr(get_settings(), "phonepe_webhook_password", "hook-secret")


async def subscribe(client, tier="pro", cycle="monthly", headers=ARTIST) -> dict:
    res = await client.post("/api/v1/subscriptions", headers=headers, json={"tier": tier, "billingCycle": cycle})
    assert res.status_code == 201, res.text
    return res.json()


async def order_of(subscription_id: str) -> str:
    async with get_sessionmaker()() as s:
        return (await s.get(Subscription, __import__("uuid").UUID(subscription_id))).gateway_subscription_id


async def webhook(client, order_id: str, *, paid=True, amount=59900, txn="T1", auth=WEBHOOK_AUTH, ts=1792662660000):
    state = "COMPLETED" if paid else "FAILED"
    body = json.dumps({"event": f"paylink.order.{'completed' if paid else 'failed'}", "payload": {
        "orderId": "OMO1", "merchantOrderId": order_id, "state": state, "amount": amount,
        "paymentDetails": [{"transactionId": txn, "amount": amount, "state": state, "timestamp": ts, "paymentMode": "UPI_QR"}]}}).encode()
    return await client.post("/api/v1/subscriptions/webhook", content=body,
                             headers={"Authorization": auth, "Content-Type": "application/json"})


async def arjun() -> ArtistProfile:
    async with get_sessionmaker()() as s:
        return (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()


async def subs() -> list[Subscription]:
    async with get_sessionmaker()() as s:
        return list((await s.execute(select(Subscription).order_by(Subscription.created_at))).scalars())


async def messages() -> list[tuple[str, dict]]:
    async with get_sessionmaker()() as s:
        return [(m.kind, m.context) for m in (await s.execute(select(QueuedMessage).order_by(QueuedMessage.created_at))).scalars()]
