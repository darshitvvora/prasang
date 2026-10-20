"""Plan entitlements (2026-10-20, three plans): Basic (free, tier key `free`), Pro, Premium — limits, embeds, badge, featured, clean-up."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.media.models import ArtistMedia
from app.notifications.models import QueuedMessage
from app.subscriptions.service import apply_tier
from tests.api.test_media import s3, s3_server  # noqa: F401  - moto S3 fixtures
from tests.helpers import ARTIST, seed_demo

ARJUN = "arjun-malhotra-magic"
MB = 1024 * 1024


async def _set_tier(tier: str, source: str = "paid") -> None:
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        await apply_tier(s, artist, tier, source if tier != "free" else "free")
        await s.commit()


async def _replace_media(images: int = 0, videos: int = 0, hd: int = 0, youtube: int = 0) -> None:
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        for m in list(artist.media):
            await s.delete(m)
        order = 0
        for kind, count in (("image", images), ("video", videos), ("hd", hd), ("youtube", youtube)):
            for i in range(count):
                is_hd = kind == "hd"
                s.add(ArtistMedia(artist_id=artist.id, kind="video" if is_hd else kind, is_hd=is_hd, display_order=order,
                                  url=f"https://cdn/{kind}{i}", storage_key=None if kind == "youtube" else f"artists/{artist.id}/{kind}{i}",
                                  embed_url="https://www.youtube-nocookie.com/embed/x" if kind == "youtube" else None))
                order += 1
        await s.commit()


async def _arjun_media(s) -> list[ArtistMedia]:
    artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
    return list((await s.execute(select(ArtistMedia).where(ArtistMedia.artist_id == artist.id)
                                 .order_by(ArtistMedia.display_order))).scalars())


async def _detail(client) -> dict:
    return (await client.get(f"/api/v1/artists/{ARJUN}")).json()


async def test_plans_reflect_new_limits(client):
    await seed_demo()
    plans = {p["tier"]: p for p in (await client.get("/api/v1/subscriptions/plans")).json()["items"]}
    assert list(plans) == ["free", "pro", "premium"]
    assert [plans[t]["name"] for t in plans] == ["Basic", "Pro", "Premium"]
    assert [(plans[t]["monthlyPrice"], plans[t]["leadLimitMonthly"], plans[t]["maxImages"], plans[t]["maxVideos"],
             plans[t]["maxHdVideos"]) for t in plans] == [(0, 3, 0, 0, 0), (599, 15, 5, 1, 0), (1199, -1, 50, 8, 2)]


async def test_basic_free_profile_shows_embeds_and_widgets(client):
    await seed_demo()
    await _replace_media(youtube=1)
    await _set_tier("free")
    body = await _detail(client)
    assert [m["kind"] for m in body["media"]] == ["youtube"]
    assert body["socialWidgets"]


async def test_badge_only_on_premium(client):
    await seed_demo()
    async with get_sessionmaker()() as s:
        (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one().is_verified = True
        await s.commit()
    await _set_tier("pro")
    assert (await _detail(client))["isVerified"] is False
    await _set_tier("premium")
    assert (await _detail(client))["isVerified"] is True


async def test_only_premium_is_featured():
    await seed_demo()
    await _set_tier("pro")
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one().is_featured is False
    await _set_tier("premium")
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one().is_featured is True


async def _upload_url(client, kind="video", size=10 * MB, hd=False, content_type="video/mp4"):
    return await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST,
                             json={"kind": kind, "contentType": content_type, "sizeBytes": size, "hd": hd})


async def test_video_size_caps(client, s3):  # noqa: F811
    await seed_demo()
    await _replace_media()
    await _set_tier("premium")
    assert (await _upload_url(client, size=40 * MB)).status_code == 200
    res = await _upload_url(client, size=40 * MB + 1)
    assert res.status_code == 422 and "sizeBytes" in res.json()["error"]["details"]["fields"]
    assert (await _upload_url(client, size=200 * MB, hd=True)).status_code == 200
    assert (await _upload_url(client, size=200 * MB + 1, hd=True)).status_code == 422


async def test_hd_only_on_premium(client, s3):  # noqa: F811
    await seed_demo()
    await _replace_media()
    await _set_tier("pro")
    res = await _upload_url(client, size=50 * MB, hd=True)
    assert res.status_code == 409 and res.json()["error"]["code"] == "media_quota_exceeded"


async def test_hd_quota_is_two(client, s3):  # noqa: F811
    await seed_demo()
    await _replace_media(hd=2)
    await _set_tier("premium")
    res = await _upload_url(client, size=50 * MB, hd=True)
    assert res.status_code == 409
    quota = (await client.get("/api/v1/artists/me/media", headers=ARTIST)).json()["quota"]
    assert quota["hdVideos"] == {"used": 2, "limit": 2}


async def test_free_cannot_upload(client, s3):  # noqa: F811
    await seed_demo()
    await _replace_media()
    await _set_tier("free")
    res = await _upload_url(client, kind="image", size=MB, content_type="image/jpeg")
    assert res.status_code == 409 and res.json()["error"]["code"] == "media_quota_exceeded"


async def test_downgrade_hides_extras_and_schedules_deletion(client):
    await seed_demo()
    await _replace_media(images=7, videos=2)
    await _set_tier("premium")
    await _set_tier("pro")
    async with get_sessionmaker()() as s:
        rows = await _arjun_media(s)
        hidden = [r for r in rows if r.hidden_at is not None]
        assert [r.url for r in hidden] == ["https://cdn/image5", "https://cdn/image6", "https://cdn/video1"]
        assert all(timedelta(days=6, hours=23) < r.delete_after - datetime.now(UTC) <= timedelta(days=7) for r in hidden)
        msg = (await s.execute(select(QueuedMessage).where(QueuedMessage.kind == "media_removal"))).scalar_one()
        assert msg.context["count"] == 3
    body = await _detail(client)
    assert len(body["media"]) == 6
    listing = (await client.get("/api/v1/artists/me/media", headers=ARTIST)).json()
    assert listing["quota"]["images"] == {"used": 5, "limit": 5}
    assert sum(1 for m in listing["items"] if m["deleteAfter"]) == 3


async def test_basic_downgrade_hides_uploads_but_keeps_embeds():
    await seed_demo()
    await _replace_media(images=1, youtube=1)
    await _set_tier("pro")
    await _set_tier("free")
    async with get_sessionmaker()() as s:
        rows = await _arjun_media(s)
        assert [(r.kind, r.hidden_at is not None) for r in rows] == [("image", True), ("youtube", False)]


async def test_upgrade_restores_hidden_items():
    await seed_demo()
    await _replace_media(images=7)
    await _set_tier("pro")
    await _set_tier("premium")
    async with get_sessionmaker()() as s:
        assert all(r.hidden_at is None and r.delete_after is None for r in await _arjun_media(s))


async def test_purge_deletes_after_7_days(monkeypatch):
    from app.sweeps import purge_hidden_media

    started = []

    class Starter:
        async def start_media_deletion(self, user_id, keys):
            started.append((user_id, keys))

    await seed_demo()
    await _replace_media(images=7)
    await _set_tier("pro")
    async with get_sessionmaker()() as s:
        assert await purge_hidden_media(s, Starter()) == 0
        assert await purge_hidden_media(s, Starter(), now=datetime.now(UTC) + timedelta(days=8)) == 2
        assert len(await _arjun_media(s)) == 5
    [(_, keys)] = started
    assert sorted(k.rsplit("/", 1)[1] for k in keys) == ["image5", "image6"]


async def test_downgrade_preview(client):
    await seed_demo()
    await _replace_media(images=7, videos=2, youtube=1)
    await _set_tier("premium")
    res = await client.get("/api/v1/subscriptions/downgrade-preview?tier=pro", headers=ARTIST)
    assert res.status_code == 200
    assert res.json() == {"tier": "pro", "photos": 2, "videos": 1, "hdVideos": 0, "embeds": 0}
    res = await client.get("/api/v1/subscriptions/downgrade-preview?tier=free", headers=ARTIST)
    assert res.json() == {"tier": "free", "photos": 7, "videos": 2, "hdVideos": 0, "embeds": 0}


@pytest.mark.parametrize("tier", ["free", "pro", "premium"])
async def test_search_card_badge_follows_plan(client, tier):
    from app.artists.views import to_card

    await seed_demo()
    await _set_tier(tier)
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        artist.is_verified = True
        assert to_card(artist).is_verified is (tier == "premium")


async def test_basic_can_add_embedded_posts(client):
    await seed_demo()
    await _replace_media()
    await _set_tier("free")
    res = await client.post("/api/v1/artists/me/media", headers=ARTIST,
                            json={"kind": "youtube", "url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ"})
    assert res.status_code == 201
