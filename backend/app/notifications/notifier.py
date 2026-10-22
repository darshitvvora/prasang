"""Outbound SMS / WhatsApp / email. Locally everything goes to the log (ConsoleNotifier)."""
import asyncio
import json
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Protocol

import httpx

from app.config import Settings, get_settings
from app.notifications.texts import WHATSAPP_AUTH_KINDS, TextMessage

log = logging.getLogger("prasang.notify")


class NotificationRejected(Exception):
    """The provider refused the message (bad number/template). Retrying won't help."""


class Notifier(Protocol):
    async def send_text(self, phone: str, message: TextMessage) -> None: ...  # SMS or WhatsApp, whichever is set up
    async def send_sms(self, phone: str, message: TextMessage) -> None: ...
    async def send_whatsapp(self, phone: str, message: TextMessage) -> None: ...
    async def send_email(self, to: str, subject: str, text: str) -> None: ...


class ConsoleNotifier:
    async def send_text(self, phone: str, message: TextMessage) -> None:
        log.warning("Text to %s: %s", phone, message.text)

    async def send_sms(self, phone: str, message: TextMessage) -> None:
        log.warning("SMS to %s: %s", phone, message.text)

    async def send_whatsapp(self, phone: str, message: TextMessage) -> None:
        log.warning("WhatsApp to %s: %s", phone, message.text)

    async def send_email(self, to: str, subject: str, text: str) -> None:
        log.warning("Email to %s [%s]: %s", to, subject, text)


def _intl(phone: str) -> str:
    """MSG91 wants 91XXXXXXXXXX: accepts 9820011001, 919820011001 and +91 98200 11001."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"91{digits}" if len(digits) == 10 else digits


class Msg91Notifier(ConsoleNotifier):
    """WhatsApp through Meta-approved templates (no DLT) and SMS through MSG91 Flow templates (DLT only), one per kind.

    Docs: https://docs.msg91.com/sms/send-sms.openapi.yml · https://docs.msg91.com/whatsapp/template-bulk.openapi.yml
    """

    API = "https://control.msg91.com"

    def __init__(self, auth_key: str, sms_templates: dict[str, str], whatsapp_number: str | None = None,
                 whatsapp_templates: dict[str, str] | None = None, whatsapp_language: str = "en", short_url: bool = True,
                 http: httpx.AsyncClient | None = None):
        self.auth_key, self.sms_templates, self.whatsapp_number = auth_key, sms_templates, whatsapp_number
        self.whatsapp_templates, self.whatsapp_language, self.short_url = whatsapp_templates or {}, whatsapp_language, short_url
        self.http = http or httpx.AsyncClient(timeout=10)

    async def _post(self, path: str, body: dict) -> dict:
        headers = {"authkey": self.auth_key, "content-type": "application/json", "accept": "application/json"}
        res = await self.http.post(f"{self.API}{path}", content=json.dumps(body), headers=headers)
        if 400 <= res.status_code < 500:
            raise NotificationRejected(f"msg91 {res.status_code}: {res.text[:200]}")
        res.raise_for_status()
        try:
            data = res.json()
        except ValueError:
            return {}
        # MSG91 answers 200 with an error body for bad templates, numbers or auth keys.
        if data.get("type") == "error" or data.get("hasError") is True or data.get("status") == "fail":
            raise NotificationRejected(f"msg91: {str(data.get('message') or data.get('errors') or data)[:200]}")
        return data

    async def send_text(self, phone: str, message: TextMessage) -> None:
        """OTP and lifecycle messages: SMS when the kind has a DLT template, else WhatsApp, else not sent."""
        if message.kind in self.sms_templates:
            await self.send_sms(phone, message)
        elif message.kind in self.whatsapp_templates and self.whatsapp_number:
            await self.send_whatsapp(phone, message)
        else:
            log.warning("no MSG91 template for %r (MSG91_WHATSAPP_TEMPLATE_%s); not sent to %s: %s",
                        message.kind, message.kind.upper(), phone, message.text)
            raise NotificationRejected(f"no MSG91 template for {message.kind}")

    async def send_sms(self, phone: str, message: TextMessage) -> None:
        template_id = self.sms_templates.get(message.kind)
        if not template_id:
            log.warning("MSG91 SMS template for %r is not configured (MSG91_SMS_TEMPLATE_%s); not sent to %s: %s",
                        message.kind, message.kind.upper(), phone, message.text)
            raise NotificationRejected(f"no MSG91 SMS template for {message.kind}")
        body = {"template_id": template_id, "recipients": [{"mobiles": _intl(phone), **message.values()}]}
        if self.short_url and "link" in message.variables:
            body["short_url"] = "1"
        await self._post("/api/v5/flow", body)

    async def send_whatsapp(self, phone: str, message: TextMessage) -> None:
        template = self.whatsapp_templates.get(message.kind)
        if not (self.whatsapp_number and template):
            raise NotificationRejected(f"WhatsApp sender number or template for {message.kind} is not configured")
        values = list(message.values("whatsapp").values())
        components = {f"body_{i}": {"type": "text", "value": value} for i, value in enumerate(values, start=1)}
        if message.kind in WHATSAPP_AUTH_KINDS:  # Authentication templates carry the code again on the copy-code button
            components["button_1"] = {"subtype": "url", "type": "text", "value": values[0]}
        await self._post("/api/v5/whatsapp/whatsapp-outbound-message/bulk/", {
            "integrated_number": self.whatsapp_number, "content_type": "template",
            "payload": {"messaging_product": "whatsapp", "type": "template", "template": {
                "name": template, "language": {"code": self.whatsapp_language, "policy": "deterministic"},
                "to_and_components": [{"to": [_intl(phone)], "components": components}]}},
        })


class SmtpEmailer:
    """Plain-text email over SMTP (SendPulse: smtp-pulse.com). Port 465 uses implicit TLS; any other port uses STARTTLS."""

    def __init__(self, host: str, port: int, username: str | None, password: str | None, sender: str):
        self.host, self.port, self.username, self.password, self.sender = host, port, username, password, sender

    def _send(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        if self.port == 465:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=15)
        with server:
            if self.port != 465:
                server.starttls(context=context)
            if self.username:
                server.login(self.username, self.password or "")
            server.send_message(message)

    async def send_email(self, to: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.sender, to, subject
        message["Message-ID"] = make_msgid(domain=self.sender.rsplit("@", 1)[-1].strip("> "))
        message.set_content(text)
        try:
            await asyncio.to_thread(self._send, message)
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as exc:
            raise NotificationRejected(f"smtp refused: {exc}") from exc
        except smtplib.SMTPResponseException as exc:
            if 500 <= exc.smtp_code < 600:  # permanent failure (bad address, sender not verified, ...)
                raise NotificationRejected(f"smtp {exc.smtp_code}: {exc.smtp_error!r}") from exc
            raise


class CompositeNotifier:
    def __init__(self, texts: ConsoleNotifier, email):
        self.texts, self.email = texts, email

    async def send_text(self, phone: str, message: TextMessage) -> None:
        await self.texts.send_text(phone, message)

    async def send_sms(self, phone: str, message: TextMessage) -> None:
        await self.texts.send_sms(phone, message)

    async def send_whatsapp(self, phone: str, message: TextMessage) -> None:
        await self.texts.send_whatsapp(phone, message)

    async def send_email(self, to: str, subject: str, text: str) -> None:
        await self.email.send_email(to, subject, text)


def get_notifier(settings: Settings | None = None) -> Notifier:
    s = settings or get_settings()
    texts = (Msg91Notifier(s.msg91_auth_key, s.msg91_templates("sms"), s.msg91_whatsapp_number, s.msg91_templates("whatsapp"),
                           s.msg91_whatsapp_language, s.msg91_short_url)
             if s.notifier != "console" and s.msg91_auth_key else ConsoleNotifier())
    email = (SmtpEmailer(s.smtp_host, s.smtp_port, s.smtp_username, s.smtp_password, s.email_sender)
             if s.smtp_host else ConsoleNotifier())
    return CompositeNotifier(texts, email)
