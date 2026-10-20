"""Payment gateway: Razorpay Subscriptions in production, a fake locally (checkout key `rzp_test_mock`)."""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from app.config import get_settings
from app.errors import AppError


class PaymentGateway(Protocol):
    key_id: str

    async def create_subscription(self, plan_id: str, total_count: int, notes: dict) -> str: ...
    async def cancel_subscription(self, gateway_subscription_id: str, at_cycle_end: bool) -> None: ...
    def verify_payment_signature(self, payment_id: str, subscription_id: str, signature: str) -> bool: ...
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool: ...
    def plan_id(self, plan, billing_cycle: str) -> str: ...
    async def fetch_subscription(self, gateway_subscription_id: str) -> dict: ...
    async def fetch_payments(self, gateway_subscription_id: str) -> list[dict]: ...
    async def invoice_url(self, invoice_id: str) -> str | None: ...


class FakeGateway:
    """Local development: no money moves; the web app's mock checkout signs with `mock-signature`."""

    key_id = "rzp_test_mock"

    async def create_subscription(self, plan_id: str, total_count: int, notes: dict) -> str:
        return f"sub_mock{secrets.token_hex(6)}"

    async def cancel_subscription(self, gateway_subscription_id: str, at_cycle_end: bool) -> None:
        return None

    def verify_payment_signature(self, payment_id: str, subscription_id: str, signature: str) -> bool:
        return hmac.compare_digest(signature, "mock-signature")

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        secret = get_settings().razorpay_webhook_secret
        return bool(secret) and hmac.compare_digest(hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(), signature)

    def plan_id(self, plan, billing_cycle: str) -> str:
        return f"plan_fake_{plan.tier}_{billing_cycle}"

    async def fetch_subscription(self, gateway_subscription_id: str) -> dict:
        end = datetime.now(UTC) + timedelta(days=30)
        return {"id": gateway_subscription_id, "status": "active", "current_end": int(end.timestamp())}

    async def fetch_payments(self, gateway_subscription_id: str) -> list[dict]:
        return []

    async def invoice_url(self, invoice_id: str) -> str | None:
        return f"{get_settings().public_web_url.rstrip('/')}/receipts/mock/{invoice_id}"


class RazorpayGateway:
    API = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str | None, http: httpx.AsyncClient | None = None):
        self.key_id, self._secret, self._webhook_secret = key_id, key_secret, webhook_secret
        self.http = http or httpx.AsyncClient(timeout=15)

    async def create_subscription(self, plan_id: str, total_count: int, notes: dict) -> str:
        res = await self.http.post(f"{self.API}/subscriptions", auth=(self.key_id, self._secret),
                                   json={"plan_id": plan_id, "total_count": total_count, "customer_notify": 1, "notes": notes})
        res.raise_for_status()
        return res.json()["id"]

    async def cancel_subscription(self, gateway_subscription_id: str, at_cycle_end: bool) -> None:
        res = await self.http.post(f"{self.API}/subscriptions/{gateway_subscription_id}/cancel", auth=(self.key_id, self._secret),
                                   json={"cancel_at_cycle_end": 1 if at_cycle_end else 0})
        res.raise_for_status()

    async def fetch_subscription(self, gateway_subscription_id: str) -> dict:
        res = await self.http.get(f"{self.API}/subscriptions/{gateway_subscription_id}", auth=(self.key_id, self._secret))
        res.raise_for_status()
        return res.json()

    async def fetch_payments(self, gateway_subscription_id: str) -> list[dict]:
        """Paid invoices of the subscription, shaped like payment entities (used to back-fill billing history)."""
        res = await self.http.get(f"{self.API}/invoices", auth=(self.key_id, self._secret),
                                  params={"subscription_id": gateway_subscription_id, "count": 100})
        res.raise_for_status()
        return [{"id": inv["payment_id"], "amount": inv.get("amount_paid") or inv.get("amount"), "currency": inv.get("currency"),
                 "status": "captured", "invoice_id": inv["id"], "created_at": inv.get("paid_at") or inv.get("created_at")}
                for inv in res.json().get("items", []) if inv.get("payment_id") and inv.get("status") == "paid"]

    async def invoice_url(self, invoice_id: str) -> str | None:
        res = await self.http.get(f"{self.API}/invoices/{invoice_id}", auth=(self.key_id, self._secret))
        res.raise_for_status()
        return res.json().get("short_url")

    def verify_payment_signature(self, payment_id: str, subscription_id: str, signature: str) -> bool:
        expected = hmac.new(self._secret.encode(), f"{payment_id}|{subscription_id}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            return False
        return hmac.compare_digest(hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest(), signature)

    def plan_id(self, plan, billing_cycle: str) -> str:
        plan_id = plan.gateway_plan_annual if billing_cycle == "annual" else plan.gateway_plan_monthly
        if not plan_id:
            raise AppError(503, "payments_not_configured", "Payments for this plan aren't set up yet. Please try again later.")
        return plan_id


def get_gateway() -> PaymentGateway:
    s = get_settings()
    if s.payment_gateway == "razorpay" and s.razorpay_key_id and s.razorpay_key_secret:
        return RazorpayGateway(s.razorpay_key_id, s.razorpay_key_secret, s.razorpay_webhook_secret)
    return FakeGateway()
