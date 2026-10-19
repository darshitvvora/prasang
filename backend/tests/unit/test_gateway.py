import hashlib
import hmac

import httpx

from app.subscriptions.gateway import FakeGateway, RazorpayGateway


def test_razorpay_payment_signature_vector():
    g = RazorpayGateway(key_id="rzp_test_x", key_secret="secret", webhook_secret="whsec")
    sig = hmac.new(b"secret", b"pay_1|sub_1", hashlib.sha256).hexdigest()
    assert g.verify_payment_signature("pay_1", "sub_1", sig)
    assert not g.verify_payment_signature("pay_1", "sub_1", "0" * 64)


def test_razorpay_webhook_signature():
    g = RazorpayGateway(key_id="k", key_secret="s", webhook_secret="whsec")
    body = b'{"event":"subscription.charged"}'
    assert g.verify_webhook_signature(body, hmac.new(b"whsec", body, hashlib.sha256).hexdigest())
    assert not g.verify_webhook_signature(body, "bad")


async def test_razorpay_create_subscription_calls_api():
    def handler(request: httpx.Request):
        assert request.url.path == "/v1/subscriptions" and request.headers["authorization"].startswith("Basic ")
        return httpx.Response(200, json={"id": "sub_ABC"})

    g = RazorpayGateway(key_id="k", key_secret="s", webhook_secret="w", http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await g.create_subscription("plan_X", 12, {"subscription_id": "s1"}) == "sub_ABC"


async def test_fake_gateway():
    g = FakeGateway()
    assert g.key_id == "rzp_test_mock"
    assert (await g.create_subscription("plan_fake", 12, {})).startswith("sub_mock")
    assert g.verify_payment_signature("p", "s", "mock-signature") and not g.verify_payment_signature("p", "s", "x")
