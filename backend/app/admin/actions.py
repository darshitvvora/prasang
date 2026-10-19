"""Admin actions behind `python -m app.cli admin …`. Each one changes state, keeps search in sync (outbox) and writes an
AdminAction audit row in the same transaction. Raises AppError for anything the operator should see."""
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.auth.models import User
from app.errors import AppError, conflict, not_found
from app.outbox.emit import artist_changed
from app.reviews.models import Review
from app.reviews.ratings import recalc_rating
from app.subscriptions import service as subs
from app.subscriptions.models import Subscription, SubscriptionPlan

log = logging.getLogger(__name__)


async def revoke_sessions(user_id: str) -> None:
    """Sign the user out everywhere (web cookies and mobile tokens)."""
    from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user

    await revoke_all_sessions_for_user(user_id)


def _log(session: AsyncSession, actor: str, action: str, target_type: str, target_id, reason: str | None = None, **payload) -> None:
    session.add(AdminAction(actor=actor, action=action, target_type=target_type, target_id=str(target_id), reason=reason,
                            payload=payload))


async def _artist(session: AsyncSession, slug: str, lock: bool = False) -> ArtistProfile:
    query = select(ArtistProfile).where(ArtistProfile.slug == slug)
    artist = (await session.execute(query.with_for_update() if lock else query)).scalar_one_or_none()
    if artist is None:
        raise not_found("artist_not_found", f"No artist with slug {slug!r}")
    return artist


async def _user(session: AsyncSession, ref: str) -> User:
    """`ref` is a 10-digit phone number or a user id."""
    query = select(User).where(User.phone == ref) if ref.isdigit() and len(ref) == 10 else select(User).where(User.id == ref)
    user = (await session.execute(query)).scalars().first()
    if user is None:
        raise not_found("user_not_found", f"No user matching {ref!r}")
    return user


async def _review(session: AsyncSession, review_id: str) -> Review:
    try:
        review = await session.get(Review, uuid.UUID(review_id))
    except ValueError:
        review = None
    if review is None:
        raise not_found("review_not_found", f"No review {review_id!r}")
    return review


async def make_admin(session: AsyncSession, user_ref: str, *, actor: str) -> None:
    user = await _user(session, user_ref)
    user.role = "admin"
    _log(session, actor, "make_admin", "user", user.id)
    await session.commit()


async def set_verified(session: AsyncSession, slug: str, value: bool, *, actor: str) -> None:
    artist = await _artist(session, slug)
    artist.is_verified = value
    artist_changed(session, artist.id)
    _log(session, actor, "set_verified", "artist", artist.id, value=value)
    await session.commit()


async def set_featured(session: AsyncSession, slug: str, value: bool, *, actor: str) -> None:
    artist = await _artist(session, slug)
    plan = await session.get(SubscriptionPlan, artist.subscription_tier)
    artist.featured_override = value
    artist.is_featured = value or plan.is_featured
    artist_changed(session, artist.id)
    _log(session, actor, "set_featured", "artist", artist.id, value=value)
    await session.commit()


def _suspend(artist: ArtistProfile, reason: str) -> None:
    artist.suspended_at = artist.suspended_at or datetime.now(UTC)
    artist.suspension_reason = reason


async def suspend(session: AsyncSession, slug: str, *, actor: str, reason: str) -> None:
    """Hidden from search and its public link; billing keeps running (refund manually in Razorpay if needed)."""
    artist = await _artist(session, slug)
    _suspend(artist, reason)
    artist_changed(session, artist.id)
    _log(session, actor, "suspend", "artist", artist.id, reason)
    await session.commit()


async def restore(session: AsyncSession, slug: str, *, actor: str) -> None:
    artist = await _artist(session, slug)
    artist.suspended_at, artist.suspension_reason = None, None
    artist_changed(session, artist.id)
    _log(session, actor, "restore", "artist", artist.id)
    await session.commit()


async def grant_plan(session: AsyncSession, slug: str, tier: str, days: int, *, actor: str, reason: str) -> None:
    artist = await _artist(session, slug, lock=True)
    if await subs.current_subscription(session, artist.id) is not None:
        raise conflict("grant_conflict", "This artist has a live paid plan — use sync-subscription for payment problems")
    if await session.get(SubscriptionPlan, tier) is None or tier == "free":
        raise AppError(422, "validation_error", f"Unknown paid tier {tier!r}")
    artist.grant_ends_at = datetime.now(UTC) + timedelta(days=days)
    artist.trial_ends_at = None if artist.tier_source == "trial" else artist.trial_ends_at
    await subs.apply_tier(session, artist, tier, "grant")
    _log(session, actor, "grant_plan", "artist", artist.id, reason, tier=tier, days=days)
    await session.commit()


async def hide_review(session: AsyncSession, review_id: str, *, actor: str, reason: str) -> None:
    review = await _review(session, review_id)
    review.hidden_at, review.hidden_reason = datetime.now(UTC), reason
    await session.flush()
    await recalc_rating(session, review.artist_id)
    _log(session, actor, "hide_review", "review", review.id, reason)
    await session.commit()


async def restore_review(session: AsyncSession, review_id: str, *, actor: str) -> None:
    review = await _review(session, review_id)
    review.hidden_at, review.hidden_reason = None, None
    await session.flush()
    await recalc_rating(session, review.artist_id)
    _log(session, actor, "restore_review", "review", review.id)
    await session.commit()


async def block_user(session: AsyncSession, user_ref: str, *, actor: str, reason: str) -> None:
    """Blocked users can't use the API. A blocked artist is also suspended and their billing cancelled immediately."""
    user = await _user(session, user_ref)
    user.blocked_at = user.blocked_at or datetime.now(UTC)
    artist = (await session.execute(select(ArtistProfile).where(ArtistProfile.user_id == user.id))).scalar_one_or_none()
    cancelled = []
    if artist is not None:
        _suspend(artist, reason)
        artist_changed(session, artist.id)
        for sub in (await session.execute(select(Subscription).where(
                Subscription.artist_id == artist.id, Subscription.status.in_(subs.LIVE)))).scalars().all():
            await subs.get_gateway().cancel_subscription(sub.gateway_subscription_id, at_cycle_end=False)
            cancelled.append(sub.gateway_subscription_id)
            await subs.end(session, sub, "cancelled", commit=False)
    _log(session, actor, "block_user", "user", user.id, reason, cancelled=cancelled)
    await session.commit()
    if artist is not None:
        for sub in (await session.execute(select(Subscription).where(
                Subscription.gateway_subscription_id.in_(cancelled)))).scalars():
            await subs.signal_ended(sub)
    try:
        await revoke_sessions(user.id)
    except Exception:
        log.exception("could not revoke sessions for %s (requests are refused anyway)", user.id)


async def unblock_user(session: AsyncSession, user_ref: str, *, actor: str) -> None:
    user = await _user(session, user_ref)
    user.blocked_at = None
    _log(session, actor, "unblock_user", "user", user.id)
    await session.commit()


SYNC_EVENTS = {"active": "subscription.activated", "authenticated": None, "created": None, "pending": None,
               "halted": "subscription.halted", "cancelled": "subscription.cancelled", "completed": "subscription.completed",
               "expired": "subscription.cancelled"}


async def sync_subscription(session: AsyncSession, slug: str, *, actor: str) -> None:
    """Re-read the artist's newest subscription from the gateway and apply it as if the webhook had arrived."""
    artist = await _artist(session, slug)
    sub = (await session.execute(select(Subscription).where(Subscription.artist_id == artist.id)
                                 .order_by(Subscription.created_at.desc()))).scalars().first()
    if sub is None:
        raise not_found("subscription_not_found", f"{slug} has no subscriptions")
    entity = await subs.get_gateway().fetch_subscription(sub.gateway_subscription_id)
    event = SYNC_EVENTS.get(entity.get("status", ""))
    _log(session, actor, "sync_subscription", "subscription", sub.id, gateway_status=entity.get("status"), applied=event)
    await session.commit()
    if event:
        await subs.handle_webhook(session, event, entity)
