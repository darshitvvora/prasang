"""Payment gateway: PhonePe Payment Links in production, a fake locally.

There is no auto-debit: every billing period is one payment link (first purchase, plan change or renewal). We email and
text the link; PhonePe's webhook (or a status check) tells us it was paid. Docs:
https://developer.phonepe.com/payment-gateway/payment-links/api-reference-payment-links/introduction
"""
import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

import httpx

from app.config import get_settings

FAKE_LINK_PREFIX = "mock://phonepe/"  # the web app "pays" these instantly (local dev and Mockoon)


@dataclass(frozen=True)
class PaymentLink:
    url: str
    expires_at: datetime
    gateway_order_id: str | None = None


@dataclass(frozen=True)
class LinkStatus:
    state: str  # ACTIVE | COMPLETED | FAILED | EXPIRED | CANCELLED
    gateway_order_id: str | None = None
    # Attempts shaped for record_payment: {id, amount (paise) | None, status: paid | failed, created_at (epoch s)}
    payments: list[dict] = field(default_factory=list)


class PaymentGateway(Protocol):
    async def create_link(self, order_id: str, amount_paise: int, description: str, *, name: str | None, phone: str,
                          email: str | None, expires_at: datetime) -> PaymentLink: ...
    async def cancel_link(self, order_id: str) -> None: ...
    async def link_status(self, order_id: str) -> LinkStatus: ...
    def verify_webhook(self, authorization: str) -> bool: ...


def webhook_authorized(authorization: str) -> bool:
    """PhonePe sends Authorization: SHA256(username:password) for the credentials set on the dashboard webhook."""
    s = get_settings()
    if not (s.phonepe_webhook_username and s.phonepe_webhook_password and authorization):
        return False
    expected = hashlib.sha256(f"{s.phonepe_webhook_username}:{s.phonepe_webhook_password}".encode()).hexdigest()
    received = authorization.split()[-1].lower()  # tolerate an optional "SHA256 " prefix
    return hmac.compare_digest(expected, received)


def _epoch_seconds(ts) -> int | None:
    if not ts:
        return None
    return int(ts / 1000) if ts > 10**11 else int(ts)  # PhonePe timestamps are epoch milliseconds


def normalise_payments(details: list[dict] | None) -> list[dict]:
    """PhonePe `paymentDetails` → payment rows. PENDING attempts are skipped (they end as COMPLETED or FAILED)."""
    rows = []
    for d in details or []:
        if d.get("state") not in ("COMPLETED", "FAILED") or not d.get("transactionId"):
            continue
        rows.append({"id": d["transactionId"], "amount": d.get("amount"), "currency": "INR",
                     "status": "paid" if d["state"] == "COMPLETED" else "failed", "created_at": _epoch_seconds(d.get("timestamp"))})
    return rows


class FakeGateway:
    """Local development: no money moves. Links are marked paid as soon as anyone checks their status."""

    async def create_link(self, order_id: str, amount_paise: int, description: str, *, name: str | None, phone: str,
                          email: str | None, expires_at: datetime) -> PaymentLink:
        return PaymentLink(url=f"{FAKE_LINK_PREFIX}{order_id}", expires_at=expires_at, gateway_order_id=f"OMO-mock-{order_id[-8:]}")

    async def cancel_link(self, order_id: str) -> None:
        return None

    async def link_status(self, order_id: str) -> LinkStatus:
        return LinkStatus(state="COMPLETED", gateway_order_id=f"OMO-mock-{order_id[-8:]}",
                          payments=[{"id": f"mock-{order_id}", "amount": None, "status": "paid", "created_at": int(time.time())}])

    def verify_webhook(self, authorization: str) -> bool:
        return webhook_authorized(authorization)


class PhonePeError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"phonepe {status} {code}: {message}")
        self.status, self.code = status, code


_tokens: dict[str, tuple[str, float]] = {}  # client_id -> (access_token, expires_at epoch s); shared across requests


class PhonePeGateway:
    HOSTS = {
        "sandbox": ("https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token",
                    "https://api-preprod.phonepe.com/apis/pg-sandbox/paylinks/v1"),
        "production": ("https://api.phonepe.com/apis/identity-manager/v1/oauth/token",
                       "https://api.phonepe.com/apis/pg/paylinks/v1"),
    }

    def __init__(self, client_id: str, client_secret: str, client_version: str, env: str, http: httpx.AsyncClient | None = None):
        self.client_id, self._secret, self.client_version = client_id, client_secret, client_version
        self.token_url, self.api = self.HOSTS[env]
        self.http = http or httpx.AsyncClient(timeout=15)

    async def _token(self, refresh: bool = False) -> str:
        cached = _tokens.get(self.client_id)
        if cached and not refresh and cached[1] - 60 > time.time():
            return cached[0]
        res = await self.http.post(self.token_url, data={"client_id": self.client_id, "client_secret": self._secret,
                                                         "client_version": self.client_version, "grant_type": "client_credentials"})
        res.raise_for_status()
        body = res.json()
        _tokens[self.client_id] = (body["access_token"], float(body.get("expires_at") or time.time() + 600))
        return body["access_token"]

    async def _call(self, method: str, path: str, json: dict | None = None) -> dict:
        for attempt in (0, 1):
            headers = {"Authorization": f"O-Bearer {await self._token(refresh=attempt == 1)}", "Content-Type": "application/json"}
            res = await self.http.request(method, f"{self.api}{path}", json=json, headers=headers)
            if res.status_code == 401 and attempt == 0:
                continue  # token revoked or expired early: fetch a new one once
            if res.status_code >= 400:
                try:
                    err = res.json()
                except ValueError:
                    err = {}
                raise PhonePeError(res.status_code, err.get("code", ""), err.get("message", res.text[:200]))
            return res.json()
        raise PhonePeError(401, "UNAUTHORIZED", "token refused twice")

    async def create_link(self, order_id: str, amount_paise: int, description: str, *, name: str | None, phone: str,
                          email: str | None, expires_at: datetime) -> PaymentLink:
        customer = {"phoneNumber": phone} | ({"name": name} if name else {}) | ({"email": email} if email else {})
        body = await self._call("POST", "/pay", {
            "merchantOrderId": order_id, "amount": amount_paise, "description": description[:150],
            "paymentFlow": {"type": "PAYLINK", "customerDetails": customer, "expireAt": int(expires_at.timestamp() * 1000),
                            # We send the link ourselves (email + SMS with our wording); PhonePe's SMS would be a duplicate.
                            "notificationChannels": {"SMS": False, "EMAIL": False}},
            "metaInfo": {"udf1": order_id},
        })
        return PaymentLink(url=body["paylinkUrl"], expires_at=datetime.fromtimestamp(body["expireAt"] / 1000, UTC),
                           gateway_order_id=body.get("orderId"))

    async def cancel_link(self, order_id: str) -> None:
        try:
            await self._call("POST", f"/{order_id}/cancel")
        except PhonePeError as err:
            if err.code == "BAD_REQUEST" and "terminal" in str(err).lower():
                return  # already paid, expired or cancelled — nothing left to stop
            raise

    async def link_status(self, order_id: str) -> LinkStatus:
        body = await self._call("GET", f"/{order_id}/status?details=true")
        return LinkStatus(state=body.get("state", ""), gateway_order_id=body.get("orderId"),
                          payments=normalise_payments(body.get("paymentDetails")))

    def verify_webhook(self, authorization: str) -> bool:
        return webhook_authorized(authorization)


def get_gateway() -> PaymentGateway:
    s = get_settings()
    if s.payment_gateway != "fake" and s.phonepe_client_id and s.phonepe_client_secret:
        return PhonePeGateway(s.phonepe_client_id, s.phonepe_client_secret, s.phonepe_client_version, s.phonepe_env)
    return FakeGateway()
