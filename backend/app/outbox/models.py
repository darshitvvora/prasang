from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.timestamps import utcnow


class OutboxEvent(Base):
    """Written in the same transaction as a domain change; the projector syncs it to Elasticsearch."""

    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_pending", "id", postgresql_where=text("processed_at IS NULL")),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aggregate_type: Mapped[str] = mapped_column(String(40))
    aggregate_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
