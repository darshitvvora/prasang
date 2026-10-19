"""Plans, trials and paid subscriptions. The gateway handles money; Temporal handles the timers."""
import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.artists.service import get_own, usage_for
from app.artists.stats import IST
from app.auth.models import User
from app.contract import (
    BillingHistoryResponse,
    BillingItem,
    Checkout,
    CheckoutPrefill,
    CreateSubscriptionResponse,
    MySubscriptionResponse,
    Plan,
    PlanFeature,
    PlanUsage,
    SubscriptionSummary,
)
from app.errors import AppError, conflict, not_found
from app.leads.service import unlock_month
from app.outbox.emit import artist_changed
from app.subscriptions.gateway import PaymentGateway, get_gateway
from app.subscriptions.models import Subscription, SubscriptionPlan
from app.subscriptions.payments import billing_history, record_payment
from app.workflows.starter import get_starter

log = logging.getLogger(__name__)
TRIAL_DAYS = 7
CYCLE_DAYS = {"monthly": 30, "annual": 365}
TOTAL_COUNT = {"monthly": 120, "annual": 10}  # Razorpay needs a finite billing count


def to_plan(p: SubscriptionPlan) -> Plan:
    return Plan(tier=p.tier, name=p.name, tagline=p.tagline, monthly_price=p.monthly_price, annual_price=p.annual_price,
                annual_monthly_equivalent=p.annual_monthly_equivalent, lead_limit_monthly=p.lead_limit_monthly,
                max_images=p.max_images, max_videos=p.max_videos, popular=p.popular,
                features=[PlanFeature(**f) for f in p.features])


async def plans(session: AsyncSession) -> list[Plan]:
    return [to_plan(p) for p in (await session.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order))).scalars()]


def period_end_iso(d: date) -> str:
    """Period ends at midnight IST at the end of the given date."""
    return datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=IST).isoformat()


async def current_subscription(session: AsyncSession, artist_id) -> Subscription | None:
    """The artist's live subscription; active wins over halted, newest first (never raises on duplicates)."""
    rows = (await session.execute(select(Subscription).where(
        Subscription.artist_id == artist_id, Subscription.status.in_(("active", "halted")))
        .order_by(Subscription.created_at.desc()))).scalars().all()
    return next((r for r in rows if r.status == "active"), rows[0] if rows else None)


def _summary(sub: Subscription | None) -> SubscriptionSummary | None:
    if sub is None:
        return None
    return SubscriptionSummary(id=str(sub.id), tier=sub.tier, billing_cycle=sub.billing_cycle, status=sub.status,
                               current_period_end=sub.current_period_end, cancel_at_period_end=sub.cancel_at_period_end)


async def my_subscription(session: AsyncSession, user: User) -> MySubscriptionResponse:
    artist = (await session.execute(select(ArtistProfile).where(ArtistProfile.user_id == user.id))).scalar_one_or_none()
    if artist is None:  # contract: before POST /artists the artist is on Free with the trial available
        free = await session.get(SubscriptionPlan, "free")
        return MySubscriptionResponse(plan=PlanUsage(
            tier="free", name=free.name, status="free", lead_limit_monthly=free.lead_limit_monthly, leads_used_this_month=0,
            leads_remaining=max(free.lead_limit_monthly, 0), period_end=None, trial_ends_at=None, trial_available=True), subscription=None)
    return MySubscriptionResponse(plan=await usage_for(session, artist, datetime.now(UTC)),
                                  subscription=_summary(await current_subscription(session, artist.id)))


async def apply_tier(session: AsyncSession, artist: ArtistProfile, tier: str, source: str) -> None:
    plan = await session.get(SubscriptionPlan, tier)
    artist.subscription_tier, artist.tier_source = tier, source
    artist.search_boost_score = plan.search_boost_score
    artist.is_featured = plan.is_featured or artist.featured_override
    if source != "grant":
        artist.grant_ends_at = None
    await unlock_month(session, artist.id, datetime.now(UTC), plan.lead_limit_monthly)
    artist_changed(session, artist.id)


async def downgrade_to_free(session: AsyncSession, artist: ArtistProfile) -> None:
    await apply_tier(session, artist, "free", "free")


async def start_trial(session: AsyncSession, user: User, tier: str):
    artist = await get_own(session, user)
    if artist.trial_used or artist.tier_source != "free":
        raise conflict("trial_used", "You have already used your free trial")
    now = datetime.now(UTC)
    artist.trial_used, artist.trial_ends_at = True, now + timedelta(days=TRIAL_DAYS)
    await apply_tier(session, artist, tier, "trial")
    await session.commit()
    try:
        await get_starter().start_trial(str(artist.id), artist.trial_ends_at.isoformat())
    except Exception:
        log.exception("could not start trial timer for %s (nightly job will end it)", artist.id)
    return await usage_for(session, artist, now)


async def end_trial(session: AsyncSession, artist_id) -> None:
    artist = await session.get(ArtistProfile, artist_id)
    if artist is not None and artist.tier_source == "trial":
        await downgrade_to_free(session, artist)
        await session.commit()


async def subscribe(session: AsyncSession, user: User, tier: str, cycle: str, gateway: PaymentGateway) -> CreateSubscriptionResponse:
    artist = await get_own(session, user)
    plan = await session.get(SubscriptionPlan, tier)
    for stale in (await session.execute(select(Subscription).where(
            Subscription.artist_id == artist.id, Subscription.status == "created"))).scalars():
        stale.status = "cancelled"  # checkout was closed; stop the gateway from charging it later
        try:
            await gateway.cancel_subscription(stale.gateway_subscription_id, at_cycle_end=False)
        except Exception:
            log.warning("could not cancel stale checkout %s at the gateway", stale.gateway_subscription_id, exc_info=True)
    await session.flush()
    gateway_id = await gateway.create_subscription(gateway.plan_id(plan, cycle), TOTAL_COUNT[cycle], {"artist_id": str(artist.id)})
    sub = Subscription(artist_id=artist.id, tier=tier, billing_cycle=cycle, status="created", gateway_subscription_id=gateway_id)
    session.add(sub)
    await session.flush()
    sub.workflow_id = f"sub-{sub.id}"
    await session.commit()
    try:
        await get_starter().start_subscription(str(sub.id))
    except Exception:
        log.exception("could not start subscription timer for %s", sub.id)
    return CreateSubscriptionResponse(subscription_id=str(sub.id), checkout=Checkout(
        key_id=gateway.key_id, razorpay_subscription_id=gateway_id, name="Prasang",
        description=f"{plan.name} plan — {cycle}", prefill=CheckoutPrefill(name=user.full_name, email=user.email, contact=user.phone)))


async def _by_gateway_id(session: AsyncSession, gateway_id: str) -> Subscription | None:
    return (await session.execute(select(Subscription).where(Subscription.gateway_subscription_id == gateway_id))).scalar_one_or_none()


async def activate(session: AsyncSession, sub: Subscription, period_end: date) -> None:
    artist = await session.get(ArtistProfile, sub.artist_id)
    for previous in (await session.execute(select(Subscription).where(
            Subscription.artist_id == sub.artist_id, Subscription.status.in_(("active", "halted")), Subscription.id != sub.id))).scalars():
        previous.status = "cancelled"  # plan change: the new subscription replaces it — stop billing the old one now
        try:
            await get_gateway().cancel_subscription(previous.gateway_subscription_id, at_cycle_end=False)
        except Exception:
            log.exception("could not cancel replaced subscription %s at the gateway", previous.gateway_subscription_id)
        await _signal(previous, "ended", "cancelled")
    await session.flush()
    sub.status, sub.current_period_end, sub.cancel_at_period_end = "active", period_end, False
    await apply_tier(session, artist, sub.tier, "paid")
    await session.commit()
    await _signal(sub, "activated", period_end_iso(period_end))


async def record_charge(session: AsyncSession, sub: Subscription, period_end: date) -> None:
    sub.status, sub.current_period_end = "active", period_end
    await session.commit()
    await _signal(sub, "charged", period_end_iso(period_end))


async def end(session: AsyncSession, sub: Subscription, status: str, commit: bool = True) -> None:
    sub.status = status
    artist = await session.get(ArtistProfile, sub.artist_id)
    if artist.tier_source == "paid" and await current_subscription(session, artist.id) is None:
        await downgrade_to_free(session, artist)
    if commit:
        await session.commit()
        await signal_ended(sub)


async def signal_ended(sub: Subscription) -> None:
    await _signal(sub, "ended", sub.status)


async def _signal(sub: Subscription, name: str, arg: str) -> None:
    try:
        await get_starter().signal_subscription(str(sub.id), name, arg)
    except Exception:
        log.exception("could not signal %s to subscription %s", name, sub.id)


async def verify(session: AsyncSession, user: User, payment_id: str, gateway_sub_id: str, signature: str, gateway: PaymentGateway):
    artist = await get_own(session, user)
    if not gateway.verify_payment_signature(payment_id, gateway_sub_id, signature):
        raise AppError(400, "invalid_signature", "We couldn't verify this payment. If money was deducted, it will be refunded.")
    sub = await _by_gateway_id(session, gateway_sub_id)
    if sub is None or sub.artist_id != artist.id:
        raise not_found("subscription_not_found", "That subscription doesn't exist")
    if sub.status == "created":
        await activate(session, sub, date.today() + timedelta(days=CYCLE_DAYS[sub.billing_cycle]))
    plan = await session.get(SubscriptionPlan, sub.tier)
    price = plan.annual_price if sub.billing_cycle == "annual" else plan.monthly_price
    await record_payment(session, sub, {"id": payment_id, "status": "captured"}, gateway, fallback_amount=price * 100)
    await session.commit()
    return await usage_for(session, artist, datetime.now(UTC))


async def cancel(session: AsyncSession, user: User, gateway: PaymentGateway) -> MySubscriptionResponse:
    artist = await get_own(session, user)
    sub = await current_subscription(session, artist.id)
    if sub is None:
        raise not_found("subscription_not_found", "You don't have an active subscription")
    await gateway.cancel_subscription(sub.gateway_subscription_id, at_cycle_end=True)
    sub.cancel_at_period_end = True
    await session.commit()
    return await my_subscription(session, user)


async def payments(session: AsyncSession, user: User) -> BillingHistoryResponse:
    artist = await get_own(session, user)
    return BillingHistoryResponse(items=[BillingItem(
        id=str(p.id), paid_at=p.paid_at, tier=sub.tier, billing_cycle=sub.billing_cycle, amount=p.amount // 100,
        currency=p.currency, status=p.status, receipt_url=p.receipt_url) for p, sub in await billing_history(session, artist.id)])


async def expire_unpaid(session: AsyncSession, subscription_id: str, gateway: PaymentGateway) -> None:
    sub = await session.get(Subscription, subscription_id)
    if sub is not None and sub.status == "created":
        sub.status = "expired"
        await session.commit()
        try:
            await gateway.cancel_subscription(sub.gateway_subscription_id, at_cycle_end=False)
        except Exception:
            log.warning("gateway cancel failed for %s", sub.gateway_subscription_id, exc_info=True)


async def lapse(session: AsyncSession, subscription_id: str) -> None:
    sub = await session.get(Subscription, subscription_id)
    if sub is not None and sub.status in ("active", "halted"):
        await end(session, sub, "expired")


LIVE = ("active", "halted")
TERMINAL = ("cancelled", "expired", "completed")


async def _paid(session: AsyncSession, sub: Subscription, period_end: date) -> None:
    """A payment arrived for `sub` (activated/charged). Every state must end with the artist on what they paid for."""
    if sub.status == "active":
        await record_charge(session, sub, period_end)
        return
    if sub.status in ("created", "halted"):
        await activate(session, sub, period_end)
        return
    # Terminal (replaced checkout, lapsed, cancelled): money was taken anyway.
    other = await current_subscription(session, sub.artist_id)
    if other is None:
        await activate(session, sub, period_end)  # restore the plan they are paying for
        return
    log.error("payment for replaced subscription %s while %s is live — cancelling it at the gateway; refund manually",
              sub.gateway_subscription_id, other.gateway_subscription_id)
    try:
        await get_gateway().cancel_subscription(sub.gateway_subscription_id, at_cycle_end=False)
    except Exception:
        log.exception("could not cancel %s", sub.gateway_subscription_id)


async def handle_webhook(session: AsyncSession, event: str, entity: dict, payment: dict | None = None) -> None:
    gateway_id = entity.get("id") or (payment or {}).get("subscription_id") or ""
    sub = await _by_gateway_id(session, gateway_id)
    if sub is None:
        log.warning("webhook %s for unknown subscription %s", event, gateway_id)
        return
    if event == "payment.failed":
        if payment:
            await record_payment(session, sub, payment, get_gateway())
            await session.commit()
        return
    current_end = entity.get("current_end")
    period_end = datetime.fromtimestamp(current_end, IST).date() if current_end else None
    if event in ("subscription.activated", "subscription.charged") and period_end:
        await _paid(session, sub, period_end)
        if payment:
            await record_payment(session, sub, payment, get_gateway())
            await session.commit()
    elif event == "subscription.halted":
        if sub.status == "active":
            sub.status = "halted"
            await session.commit()
    elif event in ("subscription.cancelled", "subscription.completed"):
        if sub.status not in TERMINAL:
            await end(session, sub, "cancelled" if event == "subscription.cancelled" else "completed")
