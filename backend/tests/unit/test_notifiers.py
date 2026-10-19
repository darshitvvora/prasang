import logging

import httpx
import pytest

from app.notifications.notifier import ConsoleNotifier, Msg91Notifier, NotificationRejected, ResendEmailer


async def test_console_notifier_logs(caplog):
    caplog.set_level(logging.WARNING)
    await ConsoleNotifier().send_sms("9820011001", "hello")
    assert "SMS to 9820011001: hello" in caplog.text


async def test_msg91_sms_and_rejection():
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.url.path, request.headers["authkey"], request.read()))
        return httpx.Response(200 if b"9820011001" in request.read() else 400, json={"type": "success"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        n = Msg91Notifier(auth_key="k", sms_template_id="t1", whatsapp_number="919800000000", http=http)
        await n.send_sms("9820011001", "hello")
        assert seen[0][0] == "/api/v5/flow" and seen[0][1] == "k" and b'"mobiles":"919820011001"' in seen[0][2].replace(b" ", b"")
        with pytest.raises(NotificationRejected):
            await n.send_sms("1111111111", "x")


async def test_resend_email():
    def handler(request: httpx.Request):
        assert request.headers["authorization"] == "Bearer re_key"
        return httpx.Response(200, json={"id": "e1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        await ResendEmailer(api_key="re_key", sender="Prasang <leads@prasang.in>", http=http).send_email("a@b.com", "Hi", "text")
