"""Billing history rows from gateway payment entities (webhooks, verify, admin sync). Idempotent per payment id."""
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.subscriptions.models import Subscription, SubscriptionPayment

log = logging.getLogger(__name__)


async def record_payment(session: AsyncSession, sub: Subscription, payment: dict, gateway,
                         fallback_amount: int | None = None) -> SubscriptionPayment | None:
    """Store (or complete) one payment row; the caller commits."""
    payment_id = payment.get("id")
    if not payment_id:
        return None
    invoice_id = payment.get("invoice_id")
    receipt_url = None
    if invoice_id and payment.get("status") != "failed":
        try:
            receipt_url = await gateway.invoice_url(invoice_id)
        except Exception:
            log.warning("could not resolve receipt for invoice %s", invoice_id, exc_info=True)
    created = payment.get("created_at")
    row = {
        "subscription_id": sub.id, "gateway_payment_id": payment_id, "gateway_invoice_id": invoice_id,
        "amount": payment.get("amount") if payment.get("amount") is not None else (fallback_amount or 0),
        "currency": payment.get("currency") or "INR", "status": "failed" if payment.get("status") == "failed" else "paid",
        "paid_at": datetime.fromtimestamp(created, UTC) if created else datetime.now(UTC), "receipt_url": receipt_url,
    }
    stmt = insert(SubscriptionPayment).values(**row)
    # A payment first seen on verify (no invoice yet) gains its receipt when the charged webhook arrives.
    stmt = stmt.on_conflict_do_update(index_elements=["gateway_payment_id"], set_={
        "gateway_invoice_id": func.coalesce(SubscriptionPayment.gateway_invoice_id, stmt.excluded.gateway_invoice_id),
        "receipt_url": func.coalesce(SubscriptionPayment.receipt_url, stmt.excluded.receipt_url),
    }).returning(SubscriptionPayment.id)
    return await session.get(SubscriptionPayment, (await session.execute(stmt)).scalar_one())


async def billing_history(session: AsyncSession, artist_id) -> list[tuple[SubscriptionPayment, Subscription]]:
    return list((await session.execute(
        select(SubscriptionPayment, Subscription).join(Subscription, Subscription.id == SubscriptionPayment.subscription_id)
        .where(Subscription.artist_id == artist_id).order_by(SubscriptionPayment.paid_at.desc()))).all())
