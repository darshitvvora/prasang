"""Media: presigned S3 uploads (moto server stands in for S3), social links, quotas, ordering, avatar."""
import boto3
import httpx
import pytest
from moto.server import ThreadedMotoServer
from sqlalchemy import func, select

from app.config import get_settings
from app.db import get_sessionmaker
from app.outbox.models import OutboxEvent
from tests.helpers import ARTIST, NEW, PLANNER, seed_demo

PORT = 5055
ENDPOINT = f"http://127.0.0.1:{PORT}"
BUCKET = "prasang-media-test"


@pytest.fixture(scope="module")
def s3_server():
    server = ThreadedMotoServer(port=PORT, verbose=False)
    server.start()
    yield
    server.stop()


@pytest.fixture
def s3(s3_server, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "s3_bucket", BUCKET)
    monkeypatch.setattr(s, "s3_endpoint_url", ENDPOINT)
    monkeypatch.setattr(s, "public_media_base_url", f"{ENDPOINT}/{BUCKET}")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    client = boto3.client("s3", endpoint_url=ENDPOINT, region_name="ap-south-1", aws_access_key_id="test", aws_secret_access_key="test")
    try:
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    except client.exceptions.BucketAlreadyOwnedByYou:
        pass
    return client


async def _upload(client, kind="image", content_type="image/jpeg", data=b"\xff\xd8fake-jpeg"):
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST,
                            json={"kind": kind, "contentType": content_type, "sizeBytes": len(data)})
    assert res.status_code == 200, res.text
    target = res.json()
    async with httpx.AsyncClient() as raw:
        put = await raw.put(target["uploadUrl"], content=data, headers=target["headers"])
    assert put.status_code == 200, put.text
    return target


async def test_presigned_upload_then_confirm(client, s3):
    await seed_demo()
    target = await _upload(client)
    assert target["storageKey"].startswith("artists/") and target["expiresAt"].endswith("Z")
    res = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "image", "storageKey": target["storageKey"], "caption": "Live"})
    assert res.status_code == 201, res.text
    media = res.json()
    assert media["url"] == f"{ENDPOINT}/{BUCKET}/{target['storageKey']}" and media["embedUrl"] is None and media["displayOrder"] == 4
    listing = (await client.get("/api/v1/artists/me/media", headers=ARTIST)).json()
    assert listing["quota"] == {"images": {"used": 5, "limit": 5}, "videos": {"used": 0, "limit": 1},
                                "hdVideos": {"used": 0, "limit": 0}}  # Arjun is on Pro (5 photos + 1 video)


async def test_confirm_rejects_missing_or_foreign_keys(client, s3):
    await seed_demo()
    res = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "image", "storageKey": "artists/someone-else/x.jpg"})
    assert res.status_code == 422 and "storageKey" in res.json()["error"]["details"]["fields"]
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST, json={"kind": "image", "contentType": "image/png", "sizeBytes": 10})
    key = res.json()["storageKey"]  # never uploaded
    res = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "image", "storageKey": key})
    assert res.status_code == 422 and "storageKey" in res.json()["error"]["details"]["fields"]


async def test_upload_validation(client, s3):
    await seed_demo()
    big = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST,
                            json={"kind": "image", "contentType": "image/jpeg", "sizeBytes": 11 * 1024 * 1024})
    assert big.status_code == 422 and "sizeBytes" in big.json()["error"]["details"]["fields"]
    wrong = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST,
                              json={"kind": "video", "contentType": "image/jpeg", "sizeBytes": 100})
    assert wrong.status_code == 422 and "contentType" in wrong.json()["error"]["details"]["fields"]


async def test_quota_exceeded_on_free_plan(client, s3):
    await seed_demo()
    await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Free Artist"})
    from tests.api.test_artists import EXAMPLE
    await client.post("/api/v1/artists", headers=NEW, json=EXAMPLE | {"name": "Free Artist"})
    res = await client.post("/api/v1/artists/me/media", headers=NEW, json={"kind": "youtube", "url": "https://youtu.be/aqz-KE-bp00"})
    assert res.status_code == 201  # Basic (free) has embeds but no uploads
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=NEW, json={"kind": "video", "contentType": "video/mp4", "sizeBytes": 100})
    assert res.status_code == 409
    assert res.json()["error"] == {"code": "media_quota_exceeded", "message": res.json()["error"]["message"], "details": {"limit": 0, "used": 0}}


async def test_social_links_get_embed_urls(client):
    await seed_demo()
    res = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "facebook", "url": "https://fb.watch/abcDEF123/"})
    assert res.status_code == 201
    assert "plugins/video.php" in res.json()["embedUrl"]
    yt = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "youtube", "url": "https://youtu.be/aqz-KE-bpKQ"})
    assert yt.json()["thumbnailUrl"] == "https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg"
    bad = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "instagram", "url": "https://evil.example/p/x"})
    assert bad.status_code == 422 and "url" in bad.json()["error"]["details"]["fields"]


async def test_uploads_without_storage_are_503_but_links_work(client):
    await seed_demo()
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST, json={"kind": "image", "contentType": "image/jpeg", "sizeBytes": 10})
    assert res.status_code == 503 and res.json()["error"]["code"] == "storage_not_configured"


async def test_delete_and_reorder(client):
    await seed_demo()
    items = (await client.get("/api/v1/artists/me/media", headers=ARTIST)).json()["items"]
    ids = [m["id"] for m in items]
    res = await client.put("/api/v1/artists/me/media/order", headers=ARTIST, json={"ids": list(reversed(ids))})
    assert [m["id"] for m in res.json()["items"]] == list(reversed(ids))
    bad = await client.put("/api/v1/artists/me/media/order", headers=ARTIST, json={"ids": ids[:2]})
    assert bad.status_code == 422
    assert (await client.delete(f"/api/v1/artists/me/media/{ids[0]}", headers=ARTIST)).status_code == 204
    assert (await client.delete(f"/api/v1/artists/me/media/{ids[0]}", headers=ARTIST)).status_code == 404
    other = (await client.get("/api/v1/artists/dj-krish")).json()["media"][0]["id"]
    assert (await client.delete(f"/api/v1/artists/me/media/{other}", headers=ARTIST)).status_code == 404


async def test_avatar(client, s3):
    await seed_demo()
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST, json={"kind": "avatar", "contentType": "image/png", "sizeBytes": 8})
    target = res.json()
    assert "/avatar-" in target["storageKey"]
    async with httpx.AsyncClient() as raw:
        await raw.put(target["uploadUrl"], content=b"\x89PNGfake", headers=target["headers"])
    res = await client.post("/api/v1/artists/me/avatar", headers=ARTIST, json={"storageKey": target["storageKey"]})
    assert res.status_code == 200
    assert res.json()["profileImageUrl"].endswith(target["storageKey"])
    async with get_sessionmaker()() as s:
        events = (await s.execute(select(func.count()).select_from(OutboxEvent))).scalar_one()
    assert events == 1


async def test_planner_cannot_manage_media(client):
    await seed_demo()
    assert (await client.get("/api/v1/artists/me/media", headers=PLANNER)).status_code == 403


async def test_oversized_upload_is_rejected_and_deleted(client, s3, monkeypatch):
    """Review fix Important 5: the declared size is enforced; anything bigger never becomes a portfolio item."""
    from app.media import service
    monkeypatch.setitem(service.LIMITS, "image", 100)
    await seed_demo()
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST, json={"kind": "image", "contentType": "image/jpeg", "sizeBytes": 50})
    target = res.json()
    async with httpx.AsyncClient() as raw:
        put = await raw.put(target["uploadUrl"], content=b"x" * 500, headers=target["headers"])
    if put.status_code == 200:  # storage accepted the bigger body; confirm must refuse it
        confirm = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "image", "storageKey": target["storageKey"]})
        assert confirm.status_code == 422 and "storageKey" in confirm.json()["error"]["details"]["fields"]
    keys = [o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])]
    assert target["storageKey"] not in keys


async def test_video_upload_cannot_be_saved_as_image(client, s3):
    await seed_demo()
    res = await client.post("/api/v1/artists/me/media/upload-url", headers=ARTIST, json={"kind": "video", "contentType": "video/mp4", "sizeBytes": 4})
    target = res.json()
    async with httpx.AsyncClient() as raw:
        await raw.put(target["uploadUrl"], content=b"mp4!", headers=target["headers"])
    confirm = await client.post("/api/v1/artists/me/media", headers=ARTIST, json={"kind": "image", "storageKey": target["storageKey"]})
    assert confirm.status_code == 422 and "storageKey" in confirm.json()["error"]["details"]["fields"]
