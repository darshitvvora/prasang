import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.timestamps import utcnow


class ContactMessage(Base):
    """A message from the Contact page. Also emailed to SUPPORT_EMAIL when configured."""

    __tablename__ = "contact_messages"
    __table_args__ = (Index("ix_contact_messages_ip_created", "ip", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(255))
    topic: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
