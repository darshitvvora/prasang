import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import EventTypeEnum
from app.timestamps import Timestamps


class Review(Timestamps, Base):
    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artist_profiles.id", ondelete="CASCADE"), index=True)
    reviewer_name: Mapped[str] = mapped_column(String(120))
    rating: Mapped[int]
    event_type: Mapped[str] = mapped_column(EventTypeEnum)
    event_month: Mapped[str] = mapped_column(String(7))
    text: Mapped[str] = mapped_column(Text)
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hidden_reason: Mapped[str | None] = mapped_column(Text)
