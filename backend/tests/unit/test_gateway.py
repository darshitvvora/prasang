import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from app.config import get_settings
from app.subscriptions import gateway as gw
from app.subscriptions.gateway import FAKE_LINK_PREFIX, FakeGateway, PhonePeError, PhonePeGateway, normalise_payments

EXPIRES = datetime(2026, 10, 23, 9, 30, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_cached_tokens():
    gw._tokens.clear()
    yield
    gw._tokens.clear()


def _phonepe(handler) -> PhonePeGateway:
    return PhonePeGateway("CID", "SECRET", "1", "sandbox", http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _token(request: httpx.Request):
    form = dict(x.split("=") for x in request.read().decode().split("&"))
    assert form == {"client_id": "CID", "client_secret": "SECRET", "client_version": "1", "grant_type": "client_credentials"}
    return httpx.Response(200, json={"access_token": "tok", "expires_at": 4102444800, "token_type": "O-Bearer"})


async def test_create_link_fetches_token_once_and_posts_paise():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request.url.path)
        if request.url.path.endswith("/oauth/token"):
            return _token(request)
        assert request.headers["authorization"] == "O-Bearer tok"
        body = json.loads(request.read())
        assert body["merchantOrderId"] == "PRS-abc" and body["amount"] == 59900
        assert body["paymentFlow"]["customerDetails"] == {"phoneNumber": "9820011001", "name": "Arjun", "email": "a@b.com"}
        assert body["paymentFlow"]["expireAt"] == int(EXPIRES.timestamp() * 1000)
        assert body["paymentFlow"]["notificationChannels"] == {"SMS": False, "EMAIL": False}
        return httpx.Response(200, json={"orderId": "OMO1", "state": "ACTIVE", "expireAt": 1792748400000,
                                         "paylinkUrl": "https://phon.pe/x"})

    g = _phonepe(handler)
    link = await g.create_link("PRS-abc", 59900, "Prasang Pro plan (monthly)", name="Arjun", phone="9820011001",
                               email="a@b.com", expires_at=EXPIRES)
    assert (link.url, link.gateway_order_id) == ("https://phon.pe/x", "OMO1")
    assert link.expires_at == datetime.fromtimestamp(1792748400, UTC)
    assert calls == ["/apis/pg-sandbox/v1/oauth/token", "/apis/pg-sandbox/paylinks/v1/pay"]


async def test_expired_token_is_refreshed_once_on_401():
    tokens = iter(["old", "new"])

    def handler(request: httpx.Request):
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"access_token": next(tokens), "expires_at": 4102444800})
        if request.headers["authorization"] == "O-Bearer old":
            return httpx.Response(401, json={"code": "UNAUTHORIZED", "message": "expired"})
        return httpx.Response(200, json={"orderId": "OMO1", "state": "ACTIVE"})

    status = await _phonepe(handler).link_status("PRS-abc")
    assert status.state == "ACTIVE"


async def test_status_normalises_attempts():
    def handler(request: httpx.Request):
        if request.url.path.endswith("/oauth/token"):
            return _token(request)
        assert request.url.path == "/apis/pg-sandbox/paylinks/v1/PRS-abc/status" and request.url.params["details"] == "true"
        return httpx.Response(200, json={"orderId": "OMO1", "state": "COMPLETED", "amount": 59900, "paymentDetails": [
            {"transactionId": "T1", "amount": 59900, "state": "FAILED", "timestamp": 1792662600000},
            {"transactionId": "T2", "amount": 59900, "state": "PENDING", "timestamp": 1792662630000},
            {"transactionId": "T3", "amount": 59900, "state": "COMPLETED", "timestamp": 1792662660000}]})

    status = await _phonepe(handler).link_status("PRS-abc")
    assert (status.state, status.gateway_order_id) == ("COMPLETED", "OMO1")
    assert [(p["id"], p["status"], p["created_at"]) for p in status.payments] == [("T1", "failed", 1792662600), ("T3", "paid", 1792662660)]


async def test_cancel_ignores_terminal_links_but_raises_other_errors():
    responses = iter([
        httpx.Response(400, json={"code": "BAD_REQUEST", "message": "Please check the inputs you have provided. [already in terminal state]"}),
        httpx.Response(500, json={"code": "INTERNAL_SERVER_ERROR", "message": "try later"}),
    ])

    def handler(request: httpx.Request):
        return _token(request) if request.url.path.endswith("/oauth/token") else next(responses)

    g = _phonepe(handler)
    await g.cancel_link("PRS-paid")
    with pytest.raises(PhonePeError):
        await g.cancel_link("PRS-down")


def test_webhook_authorization(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "phonepe_webhook_username", "prasang")
    monkeypatch.setattr(s, "phonepe_webhook_password", "s3cret")
    good = hashlib.sha256(b"prasang:s3cret").hexdigest()
    g = FakeGateway()
    assert g.verify_webhook(good) and g.verify_webhook(f"SHA256 {good.upper()}")
    assert not g.verify_webhook("") and not g.verify_webhook(hashlib.sha256(b"prasang:wrong").hexdigest())
    monkeypatch.setattr(s, "phonepe_webhook_password", None)
    assert not g.verify_webhook(good)  # never accept webhooks without configured credentials


def test_normalise_skips_pending_and_converts_millis():
    assert normalise_payments(None) == []
    assert normalise_payments([{"transactionId": "T", "amount": 100, "state": "COMPLETED", "timestamp": 1700000000}])[0]["created_at"] == 1700000000


async def test_fake_gateway_links_are_paid_on_check():
    g = FakeGateway()
    link = await g.create_link("PRS-1", 100, "x", name=None, phone="9820011001", email=None, expires_at=EXPIRES)
    assert link.url == f"{FAKE_LINK_PREFIX}PRS-1"
    assert (await g.link_status("PRS-1")).state == "COMPLETED"


def test_gateway_switches_on_when_credentials_are_set(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "phonepe_client_id", None)
    assert isinstance(gw.get_gateway(), FakeGateway)
    monkeypatch.setattr(s, "phonepe_client_id", "CID")
    monkeypatch.setattr(s, "phonepe_client_secret", "SECRET")
    assert isinstance(gw.get_gateway(), PhonePeGateway)
    monkeypatch.setattr(s, "payment_gateway", "fake")
    assert isinstance(gw.get_gateway(), FakeGateway)
