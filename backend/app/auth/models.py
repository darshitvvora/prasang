from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import RoleEnum
from app.timestamps import Timestamps


class User(Timestamps, Base):
    """Prasang profile of a SuperTokens user. `id` is the SuperTokens user id."""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(10))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(RoleEnum)
    avatar_url: Mapped[str | None] = mapped_column(String(500))


class OtpRequest(Base):
    """One row per OTP SMS requested — feeds the per-phone / per-IP rate limit."""

    __tablename__ = "otp_requests"
    __table_args__ = (
        Index("ix_otp_requests_phone_created", "phone", "created_at"),
        Index("ix_otp_requests_ip_created", "ip", "created_at"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(80))
    ip: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
