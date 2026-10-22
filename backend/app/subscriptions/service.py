"""Plans, trials and paid plans. PhonePe payment links take the money; Temporal and the sweeper handle the timers.

Every paid period is one `Subscription` row with its own payment link: a purchase or plan change starts today, a renewal
(link sent RENEWAL_LEAD_DAYS before the period ends) continues from the end of the period it renews.
"""
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.artists.service import get_own, usage_for
from app.artists.stats import IST, today_ist
from app.auth.models import User
from app.contract import (
    BillingHistoryResponse,
    BillingItem,
    CreateSubscriptionResponse,
    DowngradePreview,
    MySubscriptionResponse,
    PaymentLinkInfo,
    PendingPayment,
    Plan,
    PlanFeature,
    PlanUsage,
    SubscriptionSummary,
)
from app.errors import AppError, conflict, not_found
from app.leads.service import unlock_month
from app.media.limits import overflow, reconcile
from app.notifications.queue import queue_message
from app.outbox.emit import artist_changed
from app.subscriptions.gateway import FakeGateway, LinkStatus, PaymentGateway, get_gateway
from app.subscriptions.models import Subscription, SubscriptionPlan
from app.subscriptions.payments import billing_history, record_payment
from app.workflows.starter import get_starter

log = logging.getLogger(__name__)
TRIAL_DAYS = 7
CYCLE_DAYS = {"monthly": 30, "annual": 365}
LINK_VALID = timedelta(hours=24)  # purchase / plan change: pay within a day (the workflow expires it after that)
RENEWAL_LEAD_DAYS = 5  # renewal links go out this many days before the period ends
GRACE_DAYS = 3  # a period that ends unpaid keeps its plan this long (matches the workflow and the sweeper)


def to_plan(p: SubscriptionPlan) -> Plan:
    return Plan(tier=p.tier, name=p.name, tagline=p.tagline, monthly_price=p.monthly_price, annual_price=p.annual_price,
                annual_monthly_equivalent=p.annual_monthly_equivalent, lead_limit_monthly=p.lead_limit_monthly,
                max_images=p.max_images, max_videos=p.max_videos, max_hd_videos=p.max_hd_videos, popular=p.popular,
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
            leads_remaining=max(free.lead_limit_monthly, 0), period_end=None, trial_ends_at=None, trial_available=True),
            subscription=None, pending_payment=None)
    return MySubscriptionResponse(plan=await usage_for(session, artist, datetime.now(UTC)),
                                  subscription=_summary(await current_subscription(session, artist.id)),
                                  pending_payment=await _pending(session, artist.id))


def price(plan: SubscriptionPlan, cycle: str) -> int:
    """Rupees for one period."""
    return plan.annual_price if cycle == "annual" else plan.monthly_price


def _link(sub: Subscription, plan: SubscriptionPlan) -> PaymentLinkInfo:
    return PaymentLinkInfo(url=sub.payment_url, expires_at=sub.pay_by, amount=price(plan, sub.billing_cycle))


async def _pending(session: AsyncSession, artist_id) -> PendingPayment | None:
    sub = (await session.execute(select(Subscription).where(
        Subscription.artist_id == artist_id, Subscription.status == "created", Subscription.pay_by > datetime.now(UTC))
        .order_by(Subscription.created_at.desc()))).scalars().first()
    if sub is None or not sub.payment_url:
        return None
    plan = await session.get(SubscriptionPlan, sub.tier)
    return PendingPayment(subscription_id=str(sub.id), tier=sub.tier, billing_cycle=sub.billing_cycle,
                          renewal=sub.renews_id is not None, payment=_link(sub, plan))


async def apply_tier(session: AsyncSession, artist: ArtistProfile, tier: str, source: str) -> None:
    plan = await session.get(SubscriptionPlan, tier)
    artist.subscription_tier, artist.tier_source = tier, source
    artist.search_boost_score = plan.search_boost_score
    artist.is_featured = plan.is_featured or artist.featured_override
    if source != "grant":
        artist.grant_ends_at = None
    await unlock_month(session, artist.id, datetime.now(UTC), plan.lead_limit_monthly)
    hidden, delete_after = await reconcile(session, artist, tier)
    if hidden:
        await queue_message(session, artist.user_id, "media_removal", delete_after.isoformat(),
                            {"count": hidden, "date": _day(delete_after.astimezone(IST).date())})
    artist_changed(session, artist.id)


def _day(d: date) -> str:
    return f"{d.day} {d:%b %Y}"


async def downgrade_preview(session: AsyncSession, user: User, tier: str) -> DowngradePreview:
    """How many items a move to `tier` would remove — shown before the artist confirms."""
    artist = await get_own(session, user)
    o = await overflow(session, artist, tier)
    return DowngradePreview(tier=tier, photos=len(o.photos), videos=len(o.videos), hd_videos=len(o.hd_videos), embeds=len(o.embeds))


async def downgrade_to_free(session: AsyncSession, artist: ArtistProfile) -> None:
    previous, source = artist.subscription_tier, artist.tier_source
    await apply_tier(session, artist, "free", "free")
    if previous != "free":
        plan = await session.get(SubscriptionPlan, previous)
        await queue_message(session, artist.user_id, "plan_ended", f"{source}-{today_ist().isoformat()}", {"plan": plan.name})


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


def order_id(sub_id: uuid.UUID) -> str:
    """PhonePe merchantOrderId: max 63 chars, only `-` and `_` allowed."""
    return f"PRS-{sub_id.hex}"


def _cycle_label(cycle: str) -> str:
    return "yearly" if cycle == "annual" else "monthly"


async def _new_period(session: AsyncSession, artist: ArtistProfile, plan: SubscriptionPlan, cycle: str, gateway: PaymentGateway,
                      pay_by: datetime, renews: Subscription | None = None) -> Subscription:
    """Create the unpaid period and its PhonePe link (raises if PhonePe refuses). The caller commits and starts the timer."""
    owner = await session.get(User, artist.user_id)
    sub = Subscription(id=uuid.uuid4(), artist_id=artist.id, tier=plan.tier, billing_cycle=cycle, status="created",
                       renews_id=renews.id if renews else None)
    sub.gateway_subscription_id, sub.workflow_id = order_id(sub.id), f"sub-{sub.id}"
    link = await gateway.create_link(sub.gateway_subscription_id, price(plan, cycle) * 100,
                                     f"Prasang {plan.name} plan ({_cycle_label(cycle)})", name=artist.stage_name or owner.full_name,
                                     phone=owner.phone or artist.contact_phone, email=owner.email, expires_at=pay_by)
    sub.payment_url, sub.pay_by = link.url, link.expires_at
    session.add(sub)
    await session.flush()
    context = {"plan": plan.name, "cycle": _cycle_label(cycle), "amount": f"₹{price(plan, cycle):,}", "url": link.url,
               "pay_by": _day(link.expires_at.astimezone(IST).date())}
    if renews is not None:
        context["date"] = _day(renews.current_period_end)
    await queue_message(session, artist.user_id, "renewal_due" if renews else "payment_link", str(sub.id), context)
    return sub


async def _start_timer(sub: Subscription) -> None:
    try:
        await get_starter().start_subscription(str(sub.id), sub.pay_by.isoformat())
    except Exception:
        log.exception("could not start payment timer for %s (the sweeper expires it)", sub.id)


async def _cancel_unpaid(session: AsyncSession, artist_id, gateway: PaymentGateway) -> None:
    """Close the artist's open links so only the newest one can be paid."""
    for stale in (await session.execute(select(Subscription).where(
            Subscription.artist_id == artist_id, Subscription.status == "created"))).scalars():
        stale.status = "cancelled"
        try:
            await gateway.cancel_link(stale.gateway_subscription_id)
        except Exception:
            log.warning("could not cancel payment link %s at PhonePe", stale.gateway_subscription_id, exc_info=True)
    await session.flush()


async def subscribe(session: AsyncSession, user: User, tier: str, cycle: str, gateway: PaymentGateway) -> CreateSubscriptionResponse:
    artist = await get_own(session, user)
    plan = await session.get(SubscriptionPlan, tier)
    await _cancel_unpaid(session, artist.id, gateway)
    try:
        sub = await _new_period(session, artist, plan, cycle, gateway, datetime.now(UTC) + LINK_VALID)
    except Exception:
        log.exception("could not create a PhonePe payment link for %s", artist.id)
        raise AppError(502, "payments_unavailable", "We couldn't create your payment link. Please try again in a minute.") from None
    await session.commit()
    await _start_timer(sub)
    return CreateSubscriptionResponse(subscription_id=str(sub.id), payment=_link(sub, plan))


async def _by_gateway_id(session: AsyncSession, gateway_id: str) -> Subscription | None:
    return (await session.execute(select(Subscription).where(Subscription.gateway_subscription_id == gateway_id))).scalar_one_or_none()


async def activate(session: AsyncSession, sub: Subscription, period_end: date) -> None:
    artist = await session.get(ArtistProfile, sub.artist_id)
    replaced = []
    for previous in (await session.execute(select(Subscription).where(
            Subscription.artist_id == sub.artist_id, Subscription.status.in_(LIVE), Subscription.id != sub.id))).scalars():
        # A renewal continues its period (completed); a plan change replaces the old plan from today (cancelled).
        previous.status = "completed" if previous.id == sub.renews_id else "cancelled"
        replaced.append(previous)
    await session.flush()
    sub.status, sub.current_period_end, sub.cancel_at_period_end = "active", period_end, False
    await apply_tier(session, artist, sub.tier, "paid")
    await session.commit()
    for previous in replaced:
        await _signal(previous, "ended", previous.status)
    await _signal(sub, "activated", period_end_iso(period_end))


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


async def verify(session: AsyncSession, user: User, subscription_id: str, gateway: PaymentGateway):
    """The artist says they paid: ask PhonePe and apply the answer (idempotent with the webhook). Returns (usage, paid)."""
    artist = await get_own(session, user)
    try:
        sub = await session.get(Subscription, uuid.UUID(subscription_id))
    except ValueError:
        sub = None
    if sub is None or sub.artist_id != artist.id:
        raise not_found("subscription_not_found", "That subscription doesn't exist")
    if sub.status == "created":
        try:
            status = await gateway.link_status(sub.gateway_subscription_id)
        except Exception:
            log.warning("could not read link status for %s", sub.gateway_subscription_id, exc_info=True)
        else:
            await apply_link_status(session, sub, status)
    await session.refresh(sub)
    return await usage_for(session, artist, datetime.now(UTC)), sub.status in ("active", "completed")


async def cancel(session: AsyncSession, user: User, gateway: PaymentGateway) -> MySubscriptionResponse:
    artist = await get_own(session, user)
    sub = await current_subscription(session, artist.id)
    if sub is None:
        raise not_found("subscription_not_found", "You don't have an active subscription")
    sub.cancel_at_period_end = True  # no renewal link will be sent; a renewal link already out is closed
    await _cancel_unpaid(session, artist.id, gateway)
    await session.commit()
    return await my_subscription(session, user)


async def payments(session: AsyncSession, user: User) -> BillingHistoryResponse:
    artist = await get_own(session, user)
    return BillingHistoryResponse(items=[BillingItem(
        id=str(p.id), paid_at=p.paid_at, tier=sub.tier, billing_cycle=sub.billing_cycle, amount=p.amount // 100,
        currency=p.currency, status=p.status, receipt_url=p.receipt_url) for p, sub in await billing_history(session, artist.id)])


async def expire_unpaid(session: AsyncSession, subscription_id: str, gateway: PaymentGateway) -> None:
    """The link's time is up. Check PhonePe first: a payment whose webhook we missed must still count."""
    sub = await session.get(Subscription, subscription_id)
    if sub is None or sub.status != "created":
        return
    try:
        status = await gateway.link_status(sub.gateway_subscription_id)
    except Exception:
        log.warning("could not read link status for %s; expiring it", sub.gateway_subscription_id, exc_info=True)
        status = None
    if status is not None and status.state == "COMPLETED":
        await apply_link_status(session, sub, status)
        return
    sub.status = "expired"
    await session.commit()
    if status is None or status.state == "ACTIVE":
        try:
            await gateway.cancel_link(sub.gateway_subscription_id)
        except Exception:
            log.warning("could not cancel payment link %s at PhonePe", sub.gateway_subscription_id, exc_info=True)


async def lapse(session: AsyncSession, subscription_id: str) -> None:
    sub = await session.get(Subscription, subscription_id)
    if sub is not None and sub.status in LIVE:
        await end(session, sub, "expired")


LIVE = ("active", "halted")  # halted only exists on old Razorpay rows
TERMINAL = ("cancelled", "expired", "completed")


def _flag(session: AsyncSession, sub: Subscription, action: str, why: str) -> None:
    """Something only a person can fix on the PhonePe dashboard — listed by `admin reports`."""
    session.add(AdminAction(actor="system", action=action, target_type="subscription",
                            target_id=sub.gateway_subscription_id or str(sub.id), reason=why))


async def cancel_or_flag(session: AsyncSession, sub: Subscription, why: str) -> bool:
    """Stop any further payment. Paid periods have nothing to stop; an open link is cancelled at PhonePe, and if that fails
    the row keeps its real status and is flagged for `admin reports` (never hidden)."""
    if sub.status == "created":
        try:
            await get_gateway().cancel_link(sub.gateway_subscription_id)
        except Exception:
            log.exception("could not cancel link %s at PhonePe (%s) — flagged for manual cancellation", sub.gateway_subscription_id, why)
            _flag(session, sub, "manual_cancel_needed", why)
            return False
    sub.status = "cancelled"
    return True


async def _owner_removed(session: AsyncSession, sub: Subscription) -> bool:
    artist = await session.get(ArtistProfile, sub.artist_id)
    owner = await session.get(User, artist.user_id) if artist else None
    return owner is None or owner.deleted_at is not None or owner.blocked_at is not None


async def _period_end(session: AsyncSession, sub: Subscription) -> date:
    start = today_ist()
    if sub.renews_id is not None:
        renewed = await session.get(Subscription, sub.renews_id)
        if renewed is not None and renewed.status in LIVE and renewed.current_period_end and renewed.current_period_end >= start:
            start = renewed.current_period_end  # paid early: the new period follows the current one
    return start + timedelta(days=CYCLE_DAYS[sub.billing_cycle])


async def _paid(session: AsyncSession, sub: Subscription, amount_paise: int | None) -> None:
    """PhonePe says the link was paid. Idempotent: the webhook, "I've paid" and the sweeper may all report it."""
    if sub.status == "active" or (sub.status == "completed" and sub.current_period_end):
        return
    plan = await session.get(SubscriptionPlan, sub.tier)
    if amount_paise is not None and amount_paise < price(plan, sub.billing_cycle) * 100:
        log.error("link %s paid %s paise, expected %s — not activating", sub.gateway_subscription_id, amount_paise,
                  price(plan, sub.billing_cycle) * 100)
        _flag(session, sub, "refund_needed", f"paid {amount_paise / 100:.2f} instead of {price(plan, sub.billing_cycle)}")
        await session.commit()
        return
    if await _owner_removed(session, sub):  # deleted or blocked account: never restore a plan
        log.error("payment on %s for a deleted/blocked account — refund manually", sub.gateway_subscription_id)
        sub.status = "cancelled"
        _flag(session, sub, "refund_needed", "payment received for a deleted or blocked account — refund manually")
        await session.commit()
        return
    if sub.status in TERMINAL and await current_subscription(session, sub.artist_id) is not None:
        # A replaced or expired link was paid while another plan is live: don't swap plans behind the artist's back.
        log.error("payment for replaced link %s while another plan is live — refund manually", sub.gateway_subscription_id)
        _flag(session, sub, "refund_needed", "paid a replaced payment link while another plan was live — refund manually")
        await session.commit()
        return
    period_end = await _period_end(session, sub)
    artist = await session.get(ArtistProfile, sub.artist_id)
    await queue_message(session, artist.user_id, "payment_received", str(sub.id), {
        "plan": plan.name, "amount": f"₹{price(plan, sub.billing_cycle):,}", "date": _day(period_end)})
    await activate(session, sub, period_end)


async def apply_link_status(session: AsyncSession, sub: Subscription, status: LinkStatus) -> None:
    """Record the link's payment attempts and, when it is paid, start the period. The caller's changes are committed."""
    plan = await session.get(SubscriptionPlan, sub.tier)
    paid_amount = None
    for payment in status.payments:
        await record_payment(session, sub, payment | {"invoice_id": status.gateway_order_id},
                             fallback_amount=price(plan, sub.billing_cycle) * 100)
        if payment["status"] == "paid" and payment.get("amount") is not None:
            paid_amount = (paid_amount or 0) + payment["amount"]
    await session.commit()
    if status.state == "COMPLETED":
        await _paid(session, sub, paid_amount)
    elif status.state in ("EXPIRED", "CANCELLED") and sub.status == "created":
        sub.status = "expired"
        await session.commit()


async def handle_webhook(session: AsyncSession, event: str, payload: dict) -> None:
    """`paylink.order.completed` / `paylink.order.failed`; `payload` is PhonePe's order (merchantOrderId, state, ...)."""
    from app.subscriptions.gateway import normalise_payments

    sub = await _by_gateway_id(session, payload.get("merchantOrderId") or "")
    if sub is None:
        log.warning("webhook %s for unknown payment link %s", event, payload.get("merchantOrderId"))
        return
    state = payload.get("state") or ("COMPLETED" if event == "paylink.order.completed" else "FAILED")
    await apply_link_status(session, sub, LinkStatus(state=state, gateway_order_id=payload.get("orderId"),
                                                     payments=normalise_payments(payload.get("paymentDetails"))))


async def create_due_renewals(session: AsyncSession, gateway: PaymentGateway) -> int:
    """Send one renewal link per period, RENEWAL_LEAD_DAYS before it ends (or late, within the grace days, if missed)."""
    today = today_ist()
    due = (await session.execute(select(Subscription).where(
        Subscription.status == "active", Subscription.cancel_at_period_end.is_(False),
        Subscription.current_period_end <= today + timedelta(days=RENEWAL_LEAD_DAYS),
        Subscription.current_period_end >= today - timedelta(days=GRACE_DAYS)))).scalars().all()
    created = []
    for current in due:
        renewal_exists = (await session.execute(select(Subscription.id).where(
            Subscription.renews_id == current.id, Subscription.status != "cancelled"))).first()
        open_link = (await session.execute(select(Subscription.id).where(
            Subscription.artist_id == current.artist_id, Subscription.status == "created"))).first()
        if renewal_exists or open_link:
            continue
        artist = await session.get(ArtistProfile, current.artist_id)
        if await _owner_removed(session, current):
            continue
        plan = await session.get(SubscriptionPlan, current.tier)
        # Payable until the plan would lapse: end of the last grace day (IST).
        pay_by = datetime.fromisoformat(period_end_iso(current.current_period_end + timedelta(days=GRACE_DAYS)))
        try:
            created.append(await _new_period(session, artist, plan, current.billing_cycle, gateway, pay_by, renews=current))
        except Exception:
            log.exception("could not create renewal link for subscription %s (next sweep retries)", current.id)
            await session.rollback()
            continue
        await session.commit()
    for sub in created:
        await _start_timer(sub)
    return len(created)


async def expire_overdue_links(session: AsyncSession, gateway: PaymentGateway) -> int:
    """Links past their pay-by time whose timer never ran (Temporal was down)."""
    ids = (await session.execute(select(Subscription.id).where(
        Subscription.status == "created", Subscription.pay_by < datetime.now(UTC)).limit(100))).scalars().all()
    for sub_id in ids:
        await expire_unpaid(session, str(sub_id), gateway)
    return len(ids)


async def reconcile_open_links(session: AsyncSession, gateway: PaymentGateway, min_age: timedelta = timedelta(minutes=10)) -> int:
    """Ask PhonePe about open links in case a webhook never arrived. Returns how many turned out paid."""
    if isinstance(gateway, FakeGateway):
        return 0  # the fake reports every link as paid; local links are paid from the web app instead
    rows = (await session.execute(select(Subscription).where(
        Subscription.status == "created", Subscription.pay_by >= datetime.now(UTC),
        Subscription.created_at < datetime.now(UTC) - min_age).order_by(Subscription.created_at).limit(50))).scalars().all()
    paid = 0
    for sub in rows:
        try:
            status = await gateway.link_status(sub.gateway_subscription_id)
        except Exception:
            log.warning("sweep: could not read link status for %s", sub.gateway_subscription_id, exc_info=True)
            continue
        if status.state != "ACTIVE":
            await apply_link_status(session, sub, status)
            paid += status.state == "COMPLETED"
    return paid
