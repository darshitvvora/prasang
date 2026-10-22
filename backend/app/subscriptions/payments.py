"""Billing history rows from PhonePe payment attempts (webhooks, "I've paid", sweeps, admin sync). Idempotent per payment id."""
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.subscriptions.models import Subscription, SubscriptionPayment

log = logging.getLogger(__name__)


async def record_payment(session: AsyncSession, sub: Subscription, payment: dict,
                         fallback_amount: int | None = None) -> SubscriptionPayment | None:
    """Store one payment row; the caller commits. PhonePe links have no hosted receipt (the email is the receipt)."""
    payment_id = payment.get("id")
    if not payment_id:
        return None
    invoice_id, receipt_url = payment.get("invoice_id"), payment.get("receipt_url")
    created = payment.get("created_at")
    row = {
        "subscription_id": sub.id, "gateway_payment_id": payment_id, "gateway_invoice_id": invoice_id,
        "amount": payment.get("amount") if payment.get("amount") is not None else (fallback_amount or 0),
        "currency": payment.get("currency") or "INR", "status": "failed" if payment.get("status") == "failed" else "paid",
        "paid_at": datetime.fromtimestamp(created, UTC) if created else datetime.now(UTC), "receipt_url": receipt_url,
    }
    stmt = insert(SubscriptionPayment).values(**row)
    # The same attempt arrives from the webhook, "I've paid" and the sweeper: keep the first row, fill gaps only.
    stmt = stmt.on_conflict_do_update(index_elements=["gateway_payment_id"], set_={
        "gateway_invoice_id": func.coalesce(SubscriptionPayment.gateway_invoice_id, stmt.excluded.gateway_invoice_id),
        "receipt_url": func.coalesce(SubscriptionPayment.receipt_url, stmt.excluded.receipt_url),
    }).returning(SubscriptionPayment.id)
    return await session.get(SubscriptionPayment, (await session.execute(stmt)).scalar_one())


async def billing_history(session: AsyncSession, artist_id) -> list[tuple[SubscriptionPayment, Subscription]]:
    return list((await session.execute(
        select(SubscriptionPayment, Subscription).join(Subscription, Subscription.id == SubscriptionPayment.subscription_id)
        .where(Subscription.artist_id == artist_id).order_by(SubscriptionPayment.paid_at.desc()))).all())
