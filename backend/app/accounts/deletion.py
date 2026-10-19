"""Self-serve account deletion (India DPDP Act; Google sign-in policy). Immediate, no grace period.

Kept: subscription and payment records (financial record-keeping) — they hold no contact details. Rows other people rely
on (planners' inquiries, reviews) stay but are anonymised. The users row keeps its id so foreign keys stay valid.
"""
import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.auth.models import User
from app.leads.booking import is_settled
from app.leads.models import Lead
from app.media.models import ArtistMedia
from app.notifications.models import QueuedMessage
from app.outbox.emit import artist_changed
from app.reviews.models import Review
from app.subscriptions import service as subs
from app.subscriptions.models import Subscription
from app.workflows.starter import get_starter

log = logging.getLogger(__name__)
GONE_ARTIST = "Artist no longer on Prasang"
DELETED_USER = "Deleted user"


async def _delete_artist(session: AsyncSession, artist: ArtistProfile, now: datetime) -> list[str]:
    for sub in (await session.execute(select(Subscription).where(
            Subscription.artist_id == artist.id, Subscription.status.in_((*subs.LIVE, "created"))))).scalars().all():
        try:
            await subs.get_gateway().cancel_subscription(sub.gateway_subscription_id, at_cycle_end=False)
        except Exception:
            log.exception("could not cancel %s at the gateway during account deletion — cancel it manually",
                          sub.gateway_subscription_id)
        sub.status = "cancelled"
    media = (await session.execute(select(ArtistMedia).where(ArtistMedia.artist_id == artist.id))).scalars().all()
    keys = [m.storage_key for m in media if m.storage_key]
    for m in media:
        await session.delete(m)
    artist.is_published = False
    artist.stage_name, artist.bio, artist.contact_phone, artist.whatsapp_number = GONE_ARTIST, "", "", None
    artist.instagram_handle = artist.youtube_channel = artist.youtube_channel_id = artist.facebook_url = None
    artist.google_place_url = artist.google_place_id = artist.profile_image_url = None
    artist.subscription_tier, artist.tier_source, artist.is_featured, artist.featured_override = "free", "free", False, False
    await session.execute(update(Review).where(Review.artist_id == artist.id, Review.hidden_at.is_(None))
                          .values(hidden_at=now, hidden_reason="artist_deleted"))
    artist_changed(session, artist.id)
    return keys


async def delete_account(session: AsyncSession, user: User) -> list[str]:
    """Delete (anonymise) the user's account in one transaction; returns S3 keys to remove afterwards."""
    now = datetime.now(UTC)
    keys: list[str] = []
    artist = (await session.execute(select(ArtistProfile).where(ArtistProfile.user_id == user.id).with_for_update())).scalar_one_or_none()
    if artist is not None:
        keys = await _delete_artist(session, artist, now)
    open_leads = [lead for lead in (await session.execute(select(Lead).where(Lead.planner_id == user.id))).scalars().all()
                  if not is_settled(lead)]
    await session.execute(update(Lead).where(Lead.planner_id == user.id)
                          .values(planner_name=DELETED_USER, planner_phone="", planner_email=None))
    await session.execute(update(Review).where(Review.planner_id == user.id).values(reviewer_name="Former user"))
    await session.execute(update(QueuedMessage).where(QueuedMessage.user_id == user.id, QueuedMessage.status == "pending")
                          .values(status="failed"))
    user.full_name, user.phone, user.email, user.avatar_url, user.deleted_at = DELETED_USER, None, None, None, now
    session.add(AdminAction(actor="self", action="self_delete", target_type="user", target_id=user.id, payload={
        "artist": str(artist.id) if artist else None, "media_files": len(keys)}))
    await session.commit()

    starter = get_starter()
    for lead in open_leads:
        try:
            await starter.signal_booking_settled(str(lead.id))
        except Exception:
            log.warning("could not stop booking check-ins for %s (they skip deleted planners anyway)", lead.id)
    if keys:
        try:
            await starter.start_media_deletion(user.id, keys)
        except Exception:
            log.exception("could not start media deletion for %s; delete these S3 keys manually: %s", user.id, keys)
    return keys
