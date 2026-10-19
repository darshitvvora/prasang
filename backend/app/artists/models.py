import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import ArtistTypeEnum, TierEnum, TierSourceEnum
from app.timestamps import Timestamps


class ArtistProfile(Timestamps, Base):
    __tablename__ = "artist_profiles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    stage_name: Mapped[str] = mapped_column(String(120))
    artist_type: Mapped[str] = mapped_column(ArtistTypeEnum, index=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    location_city: Mapped[str] = mapped_column(String(80), index=True)
    location_area: Mapped[str] = mapped_column(String(120))
    per_event_rate_min: Mapped[int] = mapped_column(default=0)
    per_event_rate_max: Mapped[int] = mapped_column(default=0)
    experience_years: Mapped[int] = mapped_column(default=0)
    event_types_supported: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list)
    languages_spoken: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    ready_to_travel: Mapped[bool] = mapped_column(default=False)
    instagram_handle: Mapped[str | None] = mapped_column(String(60))
    youtube_channel: Mapped[str | None] = mapped_column(String(200))
    youtube_channel_id: Mapped[str | None] = mapped_column(String(30))  # UC… id when known → channel widget
    facebook_url: Mapped[str | None] = mapped_column(String(300))
    profile_image_url: Mapped[str | None] = mapped_column(String(500))
    contact_phone: Mapped[str] = mapped_column(String(10))
    whatsapp_number: Mapped[str | None] = mapped_column(String(10))
    is_published: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_featured: Mapped[bool] = mapped_column(default=False)
    subscription_tier: Mapped[str] = mapped_column(TierEnum, default="free")
    tier_source: Mapped[str] = mapped_column(TierSourceEnum, default="free")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_used: Mapped[bool] = mapped_column(default=False)
    search_boost_score: Mapped[int] = mapped_column(default=0)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False), default=0)
    total_reviews: Mapped[int] = mapped_column(default=0)
    total_leads: Mapped[int] = mapped_column(default=0)

    media: Mapped[list["ArtistMedia"]] = relationship(  # noqa: F821
        back_populates="artist", order_by="ArtistMedia.display_order", cascade="all, delete-orphan", lazy="selectin")


class ArtistDailyStat(Base):
    """Per-day counters for dashboard month-over-month metrics."""

    __tablename__ = "artist_daily_stats"
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artist_profiles.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    profile_views: Mapped[int] = mapped_column(default=0)
    contact_clicks: Mapped[int] = mapped_column(default=0)
