"""Public site endpoints: business contact details (About/Contact pages) and the contact form."""
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.contract import ContactRequest, ContactResponse, SiteInfo
from app.db import get_session
from app.errors import AppError
from app.notifications.notifier import Notifier, get_notifier
from app.site.models import ContactMessage

log = logging.getLogger(__name__)
router = APIRouter(tags=["site"])
PER_IP_PER_HOUR = 5
TOPICS = {"general": "General", "artist_support": "Artist support", "payments": "Payments", "report": "Report a problem"}


def contact_notifier(settings: Settings = Depends(get_settings)) -> Notifier:
    return get_notifier(settings)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")  # set by our nginx in production
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


@router.get("/site-info", response_model=SiteInfo, response_model_by_alias=True)
async def site_info(settings: Settings = Depends(get_settings)):
    return SiteInfo(support_email=settings.support_email, support_phone=settings.support_phone,
                    business_address=settings.business_address)


@router.post("/contact", status_code=201, response_model=ContactResponse, response_model_by_alias=True)
async def contact(body: ContactRequest, request: Request, db: AsyncSession = Depends(get_session),
                  settings: Settings = Depends(get_settings), notifier: Notifier = Depends(contact_notifier)):
    ip, now = client_ip(request), datetime.now(UTC)
    recent = (await db.execute(select(func.count()).select_from(ContactMessage).where(
        ContactMessage.ip == ip, ContactMessage.created_at > now - timedelta(hours=1)))).scalar_one()
    if recent >= PER_IP_PER_HOUR:
        raise AppError(429, "contact_rate_limited", "You've sent several messages already. Please try again in an hour.")
    msg = ContactMessage(name=body.name, contact=body.contact, topic=body.topic, message=body.message, ip=ip, created_at=now)
    db.add(msg)
    await db.commit()
    log.info("contact message %s (%s) from %s", msg.id, body.topic, body.contact)
    if settings.support_email:
        text = f"From: {body.name} <{body.contact}>\nTopic: {TOPICS[body.topic]}\n\n{body.message}"
        try:
            await notifier.send_email(settings.support_email, f"Contact: {TOPICS[body.topic]} — {body.name}", text)
        except Exception:
            log.exception("could not email contact message %s", msg.id)
    return ContactResponse(id=str(msg.id))
