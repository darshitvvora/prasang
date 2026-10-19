"""Outbound SMS / WhatsApp / email. Locally everything goes to the log (ConsoleNotifier)."""
import json
import logging
from typing import Protocol

import httpx

from app.config import Settings, get_settings

log = logging.getLogger("prasang.notify")


class NotificationRejected(Exception):
    """The provider refused the message (bad number/template). Retrying won't help."""


class Notifier(Protocol):
    async def send_sms(self, phone: str, text: str) -> None: ...
    async def send_whatsapp(self, phone: str, text: str) -> None: ...
    async def send_email(self, to: str, subject: str, text: str) -> None: ...


class ConsoleNotifier:
    async def send_sms(self, phone: str, text: str) -> None:
        log.warning("SMS to %s: %s", phone, text)

    async def send_whatsapp(self, phone: str, text: str) -> None:
        log.warning("WhatsApp to %s: %s", phone, text)

    async def send_email(self, to: str, subject: str, text: str) -> None:
        log.warning("Email to %s [%s]: %s", to, subject, text)


def _intl(phone: str) -> str:
    return phone if phone.startswith("91") and len(phone) == 12 else f"91{phone}"


class Msg91Notifier(ConsoleNotifier):
    """SMS via MSG91 Flow API (DLT template with a `##message##` variable) and WhatsApp via MSG91's outbound API."""

    def __init__(self, auth_key: str, sms_template_id: str, whatsapp_number: str | None, http: httpx.AsyncClient | None = None):
        self.auth_key, self.sms_template_id, self.whatsapp_number = auth_key, sms_template_id, whatsapp_number
        self.http = http or httpx.AsyncClient(timeout=10)

    async def _post(self, path: str, body: dict) -> None:
        headers = {"authkey": self.auth_key, "content-type": "application/json"}
        res = await self.http.post(f"https://control.msg91.com{path}", content=json.dumps(body), headers=headers)
        if 400 <= res.status_code < 500:
            raise NotificationRejected(f"msg91 {res.status_code}: {res.text[:200]}")
        res.raise_for_status()

    async def send_sms(self, phone: str, text: str) -> None:
        await self._post("/api/v5/flow", {"template_id": self.sms_template_id, "recipients": [{"mobiles": _intl(phone), "message": text}]})

    async def send_whatsapp(self, phone: str, text: str) -> None:
        if not self.whatsapp_number:
            raise NotificationRejected("WhatsApp sender number is not configured")
        await self._post("/api/v5/whatsapp/whatsapp-outbound-message/", {
            "integrated_number": self.whatsapp_number, "content_type": "text", "payload": {"to": _intl(phone), "text": text}})


class ResendEmailer:
    def __init__(self, api_key: str, sender: str, http: httpx.AsyncClient | None = None):
        self.api_key, self.sender = api_key, sender
        self.http = http or httpx.AsyncClient(timeout=10)

    async def send_email(self, to: str, subject: str, text: str) -> None:
        res = await self.http.post("https://api.resend.com/emails", headers={"authorization": f"Bearer {self.api_key}"},
                                   json={"from": self.sender, "to": [to], "subject": subject, "text": text})
        if 400 <= res.status_code < 500:
            raise NotificationRejected(f"resend {res.status_code}: {res.text[:200]}")
        res.raise_for_status()


class CompositeNotifier:
    def __init__(self, texts: ConsoleNotifier, email):
        self.texts, self.email = texts, email

    async def send_sms(self, phone: str, text: str) -> None:
        await self.texts.send_sms(phone, text)

    async def send_whatsapp(self, phone: str, text: str) -> None:
        await self.texts.send_whatsapp(phone, text)

    async def send_email(self, to: str, subject: str, text: str) -> None:
        await self.email.send_email(to, subject, text)


def get_notifier(settings: Settings | None = None) -> Notifier:
    s = settings or get_settings()
    texts = (Msg91Notifier(s.msg91_auth_key, s.msg91_sms_template_id, s.msg91_whatsapp_number)
             if s.notifier == "msg91" and s.msg91_auth_key and s.msg91_sms_template_id else ConsoleNotifier())
    email = ResendEmailer(s.resend_api_key, s.email_sender) if s.resend_api_key else ConsoleNotifier()
    return CompositeNotifier(texts, email)
