import json
import logging

import httpx
import pytest

from app.notifications.notifier import ConsoleNotifier, Msg91Notifier, NotificationRejected, SmtpEmailer, get_notifier
from app.notifications.texts import TextMessage

OTP = TextMessage("otp", {"otp": "123456", "minutes": "10"})
LEAD = TextMessage("lead", {"planner": "Neha Kapoor", "event": "Wedding", "date": "12 Dec 2026", "budget": "₹25K–50K",
                            "phone": "9820011001", "link": "https://prasang.in/artist/leads"})


async def test_console_notifier_logs(caplog):
    caplog.set_level(logging.WARNING)
    await ConsoleNotifier().send_sms("9820011001", OTP)
    assert "SMS to 9820011001: 123456 is your Prasang login code. It expires in 10 minutes." in caplog.text


def _msg91(handler, **kw) -> Msg91Notifier:
    return Msg91Notifier(auth_key="k", sms_templates={"otp": "tpl-otp", "lead": "tpl-lead"}, http=httpx.AsyncClient(
        transport=httpx.MockTransport(handler)), **kw)


async def test_msg91_sms_uses_the_kind_template_and_variables():
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.url.path, request.headers["authkey"], json.loads(request.read())))
        return httpx.Response(200, json={"type": "success", "message": "5e1e93cad6fc054d8e759a5b"})

    n = _msg91(handler)
    await n.send_sms("+919820011001", OTP)  # SuperTokens passes E.164
    await n.send_sms("9820011001", LEAD)
    (path, key, otp), (_, _, lead) = seen
    assert (path, key) == ("/api/v5/flow", "k")
    assert otp == {"template_id": "tpl-otp", "recipients": [{"mobiles": "919820011001", "otp": "123456", "minutes": "10"}]}
    assert lead["template_id"] == "tpl-lead" and lead["short_url"] == "1"
    assert lead["recipients"][0]["link"] == "https://prasang.in/artist/leads" and lead["recipients"][0]["planner"] == "Neha Kapoor"


async def test_msg91_rejections_are_permanent():
    replies = iter([httpx.Response(200, json={"type": "error", "message": "Invalid template"}),
                    httpx.Response(401, json={"type": "error", "message": "Authentication failure"})])
    n = _msg91(lambda request: next(replies))
    for _ in range(2):
        with pytest.raises(NotificationRejected):
            await n.send_sms("9820011001", OTP)
    with pytest.raises(NotificationRejected):  # kind without a configured template: never sent
        await n.send_sms("9820011001", TextMessage("plan_ended", {"plan": "Pro", "link": "https://prasang.in/pricing"}))


async def test_msg91_whatsapp_sends_the_approved_template():
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.url.path, json.loads(request.read())))
        return httpx.Response(200, json={"status": "success", "hasError": False, "request_id": "r1"})

    n = _msg91(handler, whatsapp_number="919800000000", whatsapp_templates={"lead": "prasang_new_lead"})
    await n.send_whatsapp("9820011001", LEAD)
    [(path, body)] = seen
    assert path == "/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    assert body["integrated_number"] == "919800000000" and body["payload"]["template"]["name"] == "prasang_new_lead"
    [group] = body["payload"]["template"]["to_and_components"]
    assert group["to"] == ["919820011001"]
    assert [c["value"] for c in group["components"].values()] == [
        "Neha Kapoor", "Wedding", "12 Dec 2026", "₹25K–50K", "9820011001", "https://prasang.in/artist/leads"]
    with pytest.raises(NotificationRejected):  # no template for locked leads yet → the workflow falls back to SMS
        await n.send_whatsapp("9820011001", TextMessage("lead_locked", {"event": "x", "date": "y", "budget": "z", "link": "l"}))


async def test_send_text_prefers_dlt_sms_else_whatsapp_and_otp_uses_the_authentication_template():
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.url.path, json.loads(request.read())))
        return httpx.Response(200, json={"type": "success", "hasError": False})

    # No DLT: only WhatsApp templates are configured.
    n = Msg91Notifier(auth_key="k", sms_templates={}, whatsapp_number="919800000000",
                      whatsapp_templates={"otp": "prasang_otp", "plan_ended": "prasang_plan_ended"},
                      http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await n.send_text("+919820011001", OTP)
    await n.send_text("9820011001", TextMessage("plan_ended", {"plan": "Pro", "link": "https://prasang.in/pricing"}))
    (otp_path, otp_body), (_, ended_body) = seen
    assert otp_path.endswith("/whatsapp-outbound-message/bulk/")
    otp_components = otp_body["payload"]["template"]["to_and_components"][0]["components"]
    assert otp_components == {"body_1": {"type": "text", "value": "123456"},
                              "button_1": {"subtype": "url", "type": "text", "value": "123456"}}
    assert [c["value"] for c in ended_body["payload"]["template"]["to_and_components"][0]["components"].values()] == [
        "Pro", "https://prasang.in/pricing"]
    with pytest.raises(NotificationRejected):  # neither template configured → skipped, email still goes out
        await n.send_text("9820011001", TextMessage("welcome_planner", {"link": "https://prasang.in/search"}))
    n.sms_templates = {"otp": "tpl-otp"}  # DLT later: SMS wins for that kind
    seen.clear()
    await n.send_text("9820011001", OTP)
    assert seen[0][0] == "/api/v5/flow"


def test_variables_are_single_line_and_within_dlt_limits():
    msg = TextMessage("booking_check", {"artist": "A Very Long Stage Name For The Artist Band", "event": "wed\nding",
                                        "link": "https://prasang.in/planner/inquiries/with/a/long/path"})
    values = msg.values()
    assert len(values["artist"]) == 30 and values["event"] == "wed ding" and values["link"].endswith("/long/path")
    with pytest.raises(ValueError):
        TextMessage("otp", {"otp": "1"})


def test_whatsapp_bodies_never_end_with_a_variable():
    from app.notifications.texts import WHATSAPP_AUTH_KINDS, WHATSAPP_KINDS, whatsapp_body

    for kind in set(WHATSAPP_KINDS) - set(WHATSAPP_AUTH_KINDS):
        assert not whatsapp_body(kind).rstrip().endswith("}}") and not whatsapp_body(kind).startswith("{{")


def test_template_report_lists_every_kind_and_env_var():
    from app.config import Settings
    from app.notifications.texts import SMS_TEMPLATES, template_report

    report = template_report(Settings(msg91_whatsapp_template_otp="prasang_otp", msg91_whatsapp_number="919800000000"))
    assert "[set] MSG91_WHATSAPP_TEMPLATE_OTP" in report and "otp=WhatsApp" in report and "lead=not sent" in report
    assert all(f"MSG91_WHATSAPP_TEMPLATE_{k.upper()}" in report and f"MSG91_SMS_TEMPLATE_{k.upper()}" in report for k in SMS_TEMPLATES)


class FakeSmtp:
    sent: list = []
    refuse = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.calls = host, port, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        import smtplib

        if FakeSmtp.refuse:
            raise smtplib.SMTPRecipientsRefused({message["To"]: (550, b"no such user")})
        FakeSmtp.sent.append((self.host, self.port, self.calls, message))


async def test_smtp_email_uses_implicit_tls_on_465_and_starttls_otherwise(monkeypatch):
    import smtplib

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSmtp)
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    FakeSmtp.sent, FakeSmtp.refuse = [], False
    await SmtpEmailer("smtp-pulse.com", 465, "u@prasang.in", "pw", "Prasang <hello@prasang.in>").send_email("a@b.com", "Hi", "text")
    await SmtpEmailer("smtp-pulse.com", 2525, "u@prasang.in", "pw", "Prasang <hello@prasang.in>").send_email("a@b.com", "Hi", "text")
    (host, port, calls, msg), (_, port2, calls2, _) = FakeSmtp.sent
    assert (host, port, calls) == ("smtp-pulse.com", 465, [("login", "u@prasang.in", "pw")])
    assert (port2, calls2[0]) == (2525, "starttls")
    assert (msg["From"], msg["To"], msg["Subject"], msg.get_content().strip()) == ("Prasang <hello@prasang.in>", "a@b.com", "Hi", "text")
    assert msg["Message-ID"].endswith("@prasang.in>")


async def test_smtp_refused_recipient_is_permanent(monkeypatch):
    import smtplib

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSmtp)
    FakeSmtp.refuse = True
    try:
        with pytest.raises(NotificationRejected):
            await SmtpEmailer("smtp-pulse.com", 465, None, None, "Prasang <hello@prasang.in>").send_email("bad@b.com", "Hi", "x")
    finally:
        FakeSmtp.refuse = False


def test_providers_switch_on_when_credentials_are_set():
    from app.config import Settings

    off = get_notifier(Settings())
    assert isinstance(off.texts, ConsoleNotifier) and isinstance(off.email, ConsoleNotifier)
    on = get_notifier(Settings(smtp_host="smtp-pulse.com", msg91_auth_key="k", msg91_sms_template_otp="t"))
    assert isinstance(on.texts, Msg91Notifier) and isinstance(on.email, SmtpEmailer)
    assert on.texts.sms_templates == {"otp": "t"}
    assert isinstance(get_notifier(Settings(notifier="console", msg91_auth_key="k")).texts, ConsoleNotifier)
