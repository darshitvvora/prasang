"""Rate limits for OTP SMS (each one costs money): per phone and per client IP, rolling one hour."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import OtpRequest

PER_PHONE_PER_HOUR = 5
PER_IP_PER_HOUR = 20
WINDOW = timedelta(hours=1)
MESSAGE = "Too many codes requested. Please wait a while and try again."


async def check_and_record(session: AsyncSession, phone: str, ip: str, now: datetime | None = None) -> str | None:
    """Returns an error message when over the limit; otherwise records the request and returns None."""
    now = now or datetime.now(UTC)
    since = now - WINDOW
    by_phone = (await session.execute(select(func.count()).select_from(OtpRequest).where(
        OtpRequest.phone == phone, OtpRequest.created_at > since, OtpRequest.created_at <= now))).scalar_one()
    by_ip = (await session.execute(select(func.count()).select_from(OtpRequest).where(
        OtpRequest.ip == ip, OtpRequest.created_at > since, OtpRequest.created_at <= now))).scalar_one()
    if by_phone >= PER_PHONE_PER_HOUR or by_ip >= PER_IP_PER_HOUR:
        return MESSAGE
    session.add(OtpRequest(phone=phone, ip=ip, created_at=now))
    await session.execute(delete(OtpRequest).where(OtpRequest.created_at < now - timedelta(days=1)))  # keep the table small
    await session.commit()
    return None
