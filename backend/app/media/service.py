"""Portfolio media: presigned uploads, confirmations, social links, quotas, ordering, avatar."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.contract import (
    CreateMediaLinkRequest,
    CreateMediaUploadRequest,
    MediaListResponse,
    MediaQuota,
    QuotaCount,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.embeds import parse_embed
from app.errors import conflict, not_found, validation
from app.media.models import ArtistMedia
from app.media.storage import Storage
from app.outbox.emit import artist_changed
from app.subscriptions.entitlements import for_tier
from app.subscriptions.models import SubscriptionPlan

MB = 1024 * 1024
LIMITS = {"image": 10 * MB, "video": 40 * MB, "hd": 200 * MB, "avatar": 5 * MB}  # videos are not compressed; caps instead
HD_PREFIX = "hd-"
TYPES = {
    "image": {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"},
    "avatar": {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"},
    "video": {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"},
}


def _prefix(artist: ArtistProfile) -> str:
    return f"artists/{artist.id}/"


async def quota(session: AsyncSession, artist: ArtistProfile) -> MediaQuota:
    """Counts only visible items (ones hidden after a downgrade are on their way out)."""
    plan = await session.get(SubscriptionPlan, artist.subscription_tier)
    counted = await session.execute(select(ArtistMedia.kind, ArtistMedia.is_hd, func.count()).where(
        ArtistMedia.artist_id == artist.id, ArtistMedia.kind.in_(("image", "video")), ArtistMedia.hidden_at.is_(None))
        .group_by(ArtistMedia.kind, ArtistMedia.is_hd))
    rows = {(kind, bool(hd)): n for kind, hd, n in counted.all()}
    images = sum(n for (k, _), n in rows.items() if k == "image")
    return MediaQuota(images=QuotaCount(used=images, limit=plan.max_images),
                      videos=QuotaCount(used=rows.get(("video", False), 0), limit=plan.max_videos),
                      hd_videos=QuotaCount(used=rows.get(("video", True), 0), limit=plan.max_hd_videos))


def _check_quota(q: MediaQuota, kind: str, hd: bool = False) -> None:
    count = q.images if kind == "image" else q.hd_videos if hd else q.videos
    if count.limit >= 0 and count.used >= count.limit:
        noun = "photos" if kind == "image" else "HD videos" if hd else "videos"
        raise conflict("media_quota_exceeded", f"Your plan allows {count.limit} {noun}. Upgrade to add more.",
                       {"limit": count.limit, "used": count.used})


async def list_media(session: AsyncSession, artist: ArtistProfile) -> MediaListResponse:
    from app.artists.views import to_media
    return MediaListResponse(items=[to_media(m) for m in artist.media], quota=await quota(session, artist))


async def upload_url(session: AsyncSession, artist: ArtistProfile, req: UploadUrlRequest, storage: Storage) -> UploadUrlResponse:
    ext = TYPES[req.kind].get(req.content_type)
    if ext is None:
        raise validation({"contentType": f"Upload {', '.join(TYPES[req.kind])}"})
    hd = req.kind == "video" and req.hd
    limit = LIMITS["hd" if hd else req.kind]
    if req.size_bytes > limit:
        hint = " (HD videos up to 200 MB on Premium)" if req.kind == "video" and not hd else ""
        raise validation({"sizeBytes": f"Max {limit // MB} MB{hint}"})
    if req.kind != "avatar":
        _check_quota(await quota(session, artist), req.kind, hd)
    name = f"avatar-{uuid.uuid4().hex}" if req.kind == "avatar" else f"{HD_PREFIX if hd else ''}{uuid.uuid4().hex}"
    key = f"{_prefix(artist)}{name}.{ext}"
    url, expires = await storage.presign_put(key, req.content_type, req.size_bytes)
    return UploadUrlResponse(upload_url=url, storage_key=key, expires_at=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             headers={"Content-Type": req.content_type})


async def _require_uploaded(artist: ArtistProfile, key: str, storage: Storage, kind: str) -> None:
    """The object must be ours, of the declared kind, and within that kind's size/type limits; otherwise it is deleted."""
    name = key.removeprefix(_prefix(artist))
    avatar = kind == "avatar"
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    owned = key.startswith(_prefix(artist)) and "/" not in name and name.startswith("avatar-") == avatar
    if not owned or ext not in TYPES[kind].values():
        raise validation({"storageKey": "Upload the file first, then save it"})
    meta = await storage.head(key)
    if meta is None:
        raise validation({"storageKey": "Upload the file first, then save it"})
    size, content_type = meta
    limit = LIMITS["hd" if kind == "video" and name.startswith(HD_PREFIX) else kind]
    if size > limit or content_type not in TYPES[kind]:
        await storage.delete(key)
        raise validation({"storageKey": f"That file is too large or not a supported type (max {limit // MB or 1} MB)"})


def _next_order(artist: ArtistProfile) -> int:
    return max((m.display_order for m in artist.media), default=-1) + 1


async def add_upload(session: AsyncSession, artist: ArtistProfile, req: CreateMediaUploadRequest, storage: Storage) -> ArtistMedia:
    await _require_uploaded(artist, req.storage_key, storage, req.kind)
    hd = req.kind == "video" and req.storage_key.rsplit("/", 1)[-1].startswith(HD_PREFIX)
    _check_quota(await quota(session, artist), req.kind, hd)
    media = ArtistMedia(artist_id=artist.id, kind=req.kind, url=storage.public_url(req.storage_key), storage_key=req.storage_key,
                        caption=req.caption, display_order=_next_order(artist), is_hd=hd)
    session.add(media)
    await session.commit()
    return media


async def add_link(session: AsyncSession, artist: ArtistProfile, req: CreateMediaLinkRequest) -> ArtistMedia:
    if not for_tier(artist.subscription_tier).social_embeds:
        raise conflict("media_quota_exceeded", "Embedding Instagram, YouTube or Facebook posts needs the Basic plan or higher.",
                       {"limit": 0, "used": 0})
    embed = parse_embed(req.kind, req.url)
    thumb = None
    if embed.kind == "youtube":
        thumb = f"https://i.ytimg.com/vi/{embed.embed_url.rsplit('/', 1)[-1]}/hqdefault.jpg"
    media = ArtistMedia(artist_id=artist.id, kind=embed.kind, url=embed.url, embed_url=embed.embed_url, thumbnail_url=thumb,
                        caption=req.caption, display_order=_next_order(artist))
    session.add(media)
    await session.commit()
    return media


async def set_avatar(session: AsyncSession, artist: ArtistProfile, key: str, storage: Storage) -> str:
    await _require_uploaded(artist, key, storage, "avatar")
    artist.profile_image_url = storage.public_url(key)
    artist_changed(session, artist.id)
    await session.commit()
    return artist.profile_image_url


async def delete_media(session: AsyncSession, artist: ArtistProfile, media_id: str) -> str | None:
    media = next((m for m in artist.media if str(m.id) == media_id), None)
    if media is None:
        raise not_found("media_not_found", "That item isn't in your portfolio")
    key = media.storage_key
    artist.media.remove(media)
    await session.commit()
    return key


async def reorder(session: AsyncSession, artist: ArtistProfile, ids: list[str]) -> list[ArtistMedia]:
    current = {str(m.id): m for m in artist.media}
    if sorted(ids) != sorted(current):
        raise validation({"ids": "Send every portfolio item id exactly once"})
    for order, media_id in enumerate(ids):
        current[media_id].display_order = order
    await session.commit()
    return sorted(artist.media, key=lambda m: m.display_order)
