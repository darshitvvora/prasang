import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.auth.models import User
from app.contract import (
    BillingHistoryResponse,
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    MySubscriptionResponse,
    PlanList,
    PlanUsage,
    StartTrialRequest,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.db import get_session
from app.errors import AppError
from app.subscriptions import service
from app.subscriptions.gateway import get_gateway
from app.subscriptions.models import PaymentEvent

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
artist_only = require_role("artist")
JSON = {"response_model_by_alias": True}


@router.get("/plans", response_model=PlanList, **JSON)
async def plans(db: AsyncSession = Depends(get_session)):
    return PlanList(items=await service.plans(db))


@router.get("/me", response_model=MySubscriptionResponse, **JSON)
async def me(user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.my_subscription(db, user)


@router.post("/trial", response_model=PlanUsage, **JSON)
async def trial(body: StartTrialRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.start_trial(db, user, body.tier)


@router.post("", response_model=CreateSubscriptionResponse, status_code=201, **JSON)
async def subscribe(body: CreateSubscriptionRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.subscribe(db, user, body.tier, body.billing_cycle, get_gateway())


@router.post("/verify", response_model=VerifyPaymentResponse, **JSON)
async def verify(body: VerifyPaymentRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    usage = await service.verify(db, user, body.razorpay_payment_id, body.razorpay_subscription_id, body.razorpay_signature,
                                 get_gateway())
    return VerifyPaymentResponse(status="active" if usage.status in ("active", "cancelling") else "pending_activation", plan=usage)


@router.post("/cancel", response_model=MySubscriptionResponse, **JSON)
async def cancel(user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.cancel(db, user, get_gateway())


@router.get("/me/payments", response_model=BillingHistoryResponse, **JSON)
async def my_payments(user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.payments(db, user)


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_session)):
    body = await request.body()
    if not get_gateway().verify_webhook_signature(body, request.headers.get("x-razorpay-signature", "")):
        raise AppError(400, "invalid_signature", "Webhook signature mismatch")
    payload = await request.json()
    event_id = request.headers.get("x-razorpay-event-id") or hashlib.sha256(body).hexdigest()[:64]
    entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    payment = payload.get("payload", {}).get("payment", {}).get("entity")
    gateway_sub_id = entity.get("id") or (payment or {}).get("subscription_id")
    await db.execute(insert(PaymentEvent).values(
        id=event_id, event_type=payload.get("event", ""), gateway_subscription_id=gateway_sub_id, payload=payload,
    ).on_conflict_do_nothing())
    await db.commit()
    record = await db.get(PaymentEvent, event_id)
    if record.processed_at is not None:
        return {"ok": True, "duplicate": True}
    # If processing fails we answer 500 and leave processed_at NULL, so Razorpay's retry applies it.
    await service.handle_webhook(db, payload.get("event", ""), entity, payment)
    record = await db.get(PaymentEvent, event_id)
    record.processed_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True}
