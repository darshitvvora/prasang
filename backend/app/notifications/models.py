import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.timestamps import utcnow


class QueuedMessage(Base):
    """One outbound SMS+email to a user. Unique per (user, kind, period) so retries and sweeps never double-send."""

    __tablename__ = "outbound_messages"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "period_key", name="uq_outbound_messages_user_kind_period"),
        Index("ix_outbound_messages_status_created", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(40))
    period_key: Mapped[str] = mapped_column(String(80))
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | sent | failed
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
