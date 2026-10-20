import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import BudgetRangeEnum, EventTypeEnum, LeadSourceEnum, LeadStatusEnum
from app.timestamps import Timestamps


class Lead(Timestamps, Base):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_artist_created", "artist_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artist_profiles.id", ondelete="CASCADE"))
    planner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    planner_name: Mapped[str] = mapped_column(String(120))
    planner_phone: Mapped[str] = mapped_column(String(10))
    planner_email: Mapped[str | None] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(EventTypeEnum)
    event_date: Mapped[date | None] = mapped_column(Date)
    event_city: Mapped[str | None] = mapped_column(String(80))
    budget_range: Mapped[str] = mapped_column(BudgetRangeEnum)
    budget_min: Mapped[int]
    budget_max: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(LeadSourceEnum)
    status: Mapped[str] = mapped_column(LeadStatusEnum, default="new")
    is_locked: Mapped[bool] = mapped_column(default=False)
    # Set once the notification workflow was started; NULL rows are retried by the sweeper (Temporal was unreachable).
    notification_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Booking confirmation: the artist marking "converted" or the planner answering "booked" — whichever comes first.
    booking_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    booking_confirmed_by: Mapped[str | None] = mapped_column(String(10))  # artist | planner
    planner_answer: Mapped[str | None] = mapped_column(String(12))  # booked | not_booked | deciding
    planner_answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    followup_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = sweeper starts it
