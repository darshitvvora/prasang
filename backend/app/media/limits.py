"""Keep an artist's portfolio within their plan: items beyond the limit are hidden and deleted 7 days later.

What stays is decided by the artist's own display order (first N of each kind). On a plan without social embeds,
embedded posts are extras too. Upgrading inside the 7 days brings everything back.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.media.models import ArtistMedia
from app.subscriptions.entitlements import EMBED_KINDS, for_tier
from app.subscriptions.models import SubscriptionPlan

GRACE = timedelta(days=7)


@dataclass(frozen=True)
class Overflow:
    photos: list[ArtistMedia]
    videos: list[ArtistMedia]
    hd_videos: list[ArtistMedia]
    embeds: list[ArtistMedia]

    @property
    def all(self) -> list[ArtistMedia]:
        return self.photos + self.videos + self.hd_videos + self.embeds


def _beyond(items: list[ArtistMedia], limit: int) -> list[ArtistMedia]:
    return [] if limit < 0 else items[limit:]


async def overflow(session: AsyncSession, artist: ArtistProfile, tier: str) -> Overflow:
    plan = await session.get(SubscriptionPlan, tier)
    media = sorted(artist.media, key=lambda m: m.display_order)
    photos = [m for m in media if m.kind == "image"]
    videos = [m for m in media if m.kind == "video" and not m.is_hd]
    hd = [m for m in media if m.kind == "video" and m.is_hd]
    embeds = [m for m in media if m.kind in EMBED_KINDS]
    return Overflow(photos=_beyond(photos, plan.max_images), videos=_beyond(videos, plan.max_videos),
                    hd_videos=_beyond(hd, plan.max_hd_videos), embeds=[] if for_tier(tier).social_embeds else embeds)


async def reconcile(session: AsyncSession, artist: ArtistProfile, tier: str, now: datetime | None = None) -> tuple[int, datetime | None]:
    """Hide what no longer fits, un-hide what fits again. Returns (newly hidden count, their deletion time)."""
    now = now or datetime.now(UTC)
    extra = {m.id for m in (await overflow(session, artist, tier)).all}
    newly, delete_after = 0, now + GRACE
    for m in artist.media:
        if m.id in extra and m.hidden_at is None:
            m.hidden_at, m.delete_after = now, delete_after
            newly += 1
        elif m.id not in extra and m.hidden_at is not None:
            m.hidden_at, m.delete_after = None, None
    return newly, (delete_after if newly else None)
