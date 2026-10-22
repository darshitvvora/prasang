import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import BillingCycleEnum, SubscriptionStatusEnum, TierEnum
from app.timestamps import Timestamps, utcnow


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    tier: Mapped[str] = mapped_column(TierEnum, primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    tagline: Mapped[str] = mapped_column(String(120))
    monthly_price: Mapped[int]
    annual_price: Mapped[int]
    annual_monthly_equivalent: Mapped[int]
    lead_limit_monthly: Mapped[int]
    max_images: Mapped[int]
    max_videos: Mapped[int]
    max_hd_videos: Mapped[int] = mapped_column(default=0, server_default="0")
    popular: Mapped[bool] = mapped_column(default=False)
    search_boost_score: Mapped[int] = mapped_column(default=0)
    is_featured: Mapped[bool] = mapped_column(default=False)
    whatsapp_notifications: Mapped[bool] = mapped_column(default=False)
    features: Mapped[list] = mapped_column(JSONB, default=list)
    sort_order: Mapped[int] = mapped_column(default=0)


class Subscription(Timestamps, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("uq_subscriptions_one_active", "artist_id", unique=True, postgresql_where=text("status = 'active'")),
        Index("uq_subscriptions_one_created", "artist_id", unique=True, postgresql_where=text("status = 'created'")),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artist_profiles.id", ondelete="CASCADE"), index=True)
    tier: Mapped[str] = mapped_column(TierEnum)
    billing_cycle: Mapped[str] = mapped_column(BillingCycleEnum)
    status: Mapped[str] = mapped_column(SubscriptionStatusEnum, default="created")
    # One billing period paid by one PhonePe payment link; this is the link's merchantOrderId (PRS-<id hex>).
    gateway_subscription_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    payment_url: Mapped[str | None] = mapped_column(String(300))
    pay_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # link expiry; unpaid after this = expired
    # Set on a renewal: the period it continues. Paying it extends from that period's end instead of today.
    renews_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True)
    current_period_end: Mapped[date | None] = mapped_column(Date)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)
    workflow_id: Mapped[str | None] = mapped_column(String(120))


class PaymentEvent(Base):
    """Gateway webhook events, keyed by the gateway event id for idempotency."""

    __tablename__ = "payment_events"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60))
    gateway_subscription_id: Mapped[str | None] = mapped_column(String(80), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    signalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = received but not applied yet


class SubscriptionPayment(Base):
    """One payment attempt (paid or failed) on a subscription's payment link — the artist's billing history."""

    __tablename__ = "subscription_payments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True)
    gateway_payment_id: Mapped[str] = mapped_column(String(80), unique=True)  # PhonePe transactionId
    gateway_invoice_id: Mapped[str | None] = mapped_column(String(80))  # PhonePe orderId of the link
    amount: Mapped[int]  # paise
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(10))  # paid | failed
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    receipt_url: Mapped[str | None] = mapped_column(String(300))
