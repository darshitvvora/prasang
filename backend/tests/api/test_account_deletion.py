"""Self-serve account deletion (DPDP): immediate, after a fresh sign-in; billing stops; personal data is removed."""
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.accounts.router import session_age_seconds
from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.auth.models import User
from app.db import get_sessionmaker
from app.leads.models import Lead
from app.media.models import ArtistMedia
from app.notifications.models import QueuedMessage
from app.notifications.queue import queue_message
from app.reviews.models import Review
from app.search.es import alias, get_es
from app.search.projector import EsIndexer, project_batch, reindex_all
from app.subscriptions.gateway import FakeGateway
from app.subscriptions.models import Subscription, SubscriptionPayment
from tests.helpers import ARTIST, NEW, PLANNER, seed_demo

ARJUN = "arjun-malhotra-magic"


class RecordingGateway(FakeGateway):
    def __init__(self):
        self.cancelled: list[tuple[str, bool]] = []

    async def cancel_subscription(self, gateway_subscription_id, at_cycle_end):
        self.cancelled.append((gateway_subscription_id, at_cycle_end))


class RecordingStarter:
    def __init__(self):
        self.calls: list[tuple] = []

    def __getattr__(self, name):
        async def record(*args):
            self.calls.append((name, *args))
        return record


@pytest.fixture
def gateway(monkeypatch):
    g = RecordingGateway()
    monkeypatch.setattr("app.subscriptions.service.get_gateway", lambda: g)
    return g


@pytest.fixture
def starter(monkeypatch):
    s = RecordingStarter()
    monkeypatch.setattr("app.accounts.deletion.get_starter", lambda: s)
    monkeypatch.setattr("app.leads.booking.get_starter", lambda: s)
    return s


async def _arjun(s) -> ArtistProfile:
    return (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()


async def _neha_lead(s, artist) -> Lead:
    lead = Lead(artist_id=artist.id, planner_id="dev-planner-neha", planner_name="Neha Kulkarni", planner_phone="9920012345",
                planner_email="neha@example.com", event_type="birthday", event_date=date.today() - timedelta(days=5),
                budget_range="15k_25k", budget_min=15000, budget_max=25000, source="profile", status="converted",
                is_locked=False, created_at=datetime.now(UTC) - timedelta(days=20), booking_confirmed_at=datetime.now(UTC))
    s.add(lead)
    await s.commit()
    return lead


async def test_delete_requires_fresh_session(client):
    from app.main import create_app

    await seed_demo()
    app = create_app()
    app.dependency_overrides[session_age_seconds] = lambda: 3600
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as stale:
        res = await stale.delete("/api/v1/me", headers=PLANNER)
    assert res.status_code == 403
    body = res.json()["error"]
    assert body["code"] == "reauth_required"
    assert body["details"]["method"] in ("phone", "google")
    async with get_sessionmaker()() as s:
        assert (await s.get(User, "dev-planner-neha")).deleted_at is None


async def test_artist_delete_cancels_billing_and_hides_profile(client, gateway, starter):
    await seed_demo()
    es = get_es()
    await reindex_all(get_sessionmaker(), es)
    async with get_sessionmaker()() as s:
        artist = await _arjun(s)
        s.add(Subscription(artist_id=artist.id, tier="basic", billing_cycle="monthly", status="active",
                           gateway_subscription_id="sub_del", current_period_end=date.today() + timedelta(days=10)))
        s.add(ArtistMedia(artist_id=artist.id, kind="image", url="https://cdn/x.jpg", storage_key="artists/a/x.jpg", display_order=99))
        await s.commit()
    assert (await client.delete("/api/v1/me", headers=ARTIST)).status_code == 204
    assert gateway.cancelled == [("sub_del", False)]
    assert (await client.get(f"/api/v1/artists/{ARJUN}")).status_code == 404
    await project_batch(get_sessionmaker(), EsIndexer(es))
    await es.indices.refresh(index=alias())
    assert (await es.search(index=alias(), body={"query": {"term": {"slug": ARJUN}}}))["hits"]["total"]["value"] == 0
    await es.close()
    async with get_sessionmaker()() as s:
        artist = await _arjun(s)
        assert (artist.contact_phone, artist.whatsapp_number, artist.instagram_handle, artist.bio) == ("", None, None, "")
        assert (await s.execute(select(ArtistMedia).where(ArtistMedia.artist_id == artist.id))).scalars().all() == []
        assert (await s.execute(select(Subscription))).scalar_one().status == "cancelled"
        user = await s.get(User, "dev-artist-arjun")
        assert (user.full_name, user.phone, user.email) == ("Deleted user", None, None) and user.deleted_at is not None
        assert (await s.execute(select(AdminAction))).scalar_one().action == "self_delete"
    assert ("start_media_deletion", "dev-artist-arjun", ["artists/a/x.jpg"]) in starter.calls


async def test_artist_delete_hides_reviews_about_them(client, gateway, starter):
    await seed_demo()
    assert (await client.delete("/api/v1/me", headers=ARTIST)).status_code == 204
    async with get_sessionmaker()() as s:
        artist = await _arjun(s)
        reviews = (await s.execute(select(Review).where(Review.artist_id == artist.id))).scalars().all()
        assert reviews and all(r.hidden_at is not None and r.hidden_reason == "artist_deleted" for r in reviews)


async def test_planner_delete_anonymises_leads_and_keeps_reviews(client, gateway, starter):
    await seed_demo()
    async with get_sessionmaker()() as s:
        lead = await _neha_lead(s, await _arjun(s))
        s.add(Review(artist_id=lead.artist_id, lead_id=lead.id, planner_id="dev-planner-neha", reviewer_name="Neha K.", rating=5,
                     event_type="birthday", event_month="2026-10", text="Wonderful show for the kids, thank you!"))
        await s.commit()
        lead_id = lead.id
    assert (await client.delete("/api/v1/me", headers=PLANNER)).status_code == 204
    async with get_sessionmaker()() as s:
        lead = await s.get(Lead, lead_id)
        assert (lead.planner_name, lead.planner_phone, lead.planner_email) == ("Deleted user", "", None)
        review = (await s.execute(select(Review).where(Review.lead_id == lead_id))).scalar_one()
        assert (review.reviewer_name, review.hidden_at) == ("Former user", None)
    signalled = [c[1] for c in starter.calls if c[0] == "signal_booking_settled"]
    assert signalled and str(lead_id) not in signalled  # open inquiries stop their check-ins; confirmed ones have none


async def test_deleted_user_messages_not_sent(client, gateway, starter):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await queue_message(s, "dev-planner-neha", "welcome_planner", "test")
        await s.commit()
    await client.delete("/api/v1/me", headers=PLANNER)
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(QueuedMessage))).scalar_one().status == "failed"


async def test_payment_records_kept_without_contact(client, gateway, starter):
    await seed_demo()
    async with get_sessionmaker()() as s:
        artist = await _arjun(s)
        sub = Subscription(artist_id=artist.id, tier="basic", billing_cycle="monthly", status="active", gateway_subscription_id="sub_k",
                           current_period_end=date.today() + timedelta(days=10))
        s.add(sub)
        await s.flush()
        s.add(SubscriptionPayment(subscription_id=sub.id, gateway_payment_id="pay_k", amount=29900, currency="INR", status="paid",
                                  paid_at=datetime.now(UTC)))
        await s.commit()
    await client.delete("/api/v1/me", headers=ARTIST)
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(SubscriptionPayment))).scalar_one().amount == 29900


async def test_deleted_user_session_is_gone(client, gateway, starter):
    await seed_demo()
    await client.delete("/api/v1/me", headers=PLANNER)
    res = await client.get("/api/v1/me", headers=PLANNER)
    assert res.status_code == 401


async def test_same_phone_signs_up_as_new_user(client, gateway, starter):
    """A new sign-in with the same phone gets a new SuperTokens id → a fresh, empty Prasang account."""
    await seed_demo()
    async with get_sessionmaker()() as s:
        lead = await _neha_lead(s, await _arjun(s))
        lead_id = lead.id
    await client.delete("/api/v1/me", headers=PLANNER)
    res = await client.get("/api/v1/me", headers=NEW)  # stands in for the new identity
    assert res.status_code == 404 and res.json()["error"]["code"] == "profile_required"
    assert (await client.post("/api/v1/me", headers=NEW, json={"role": "planner", "fullName": "Neha Again"})).status_code == 201
    assert (await client.get("/api/v1/leads/planner", headers=NEW)).json()["total"] == 0
    async with get_sessionmaker()() as s:
        assert (await s.get(Lead, lead_id)).planner_name == "Deleted user"


async def test_inquiry_shows_artist_gone(client, gateway, starter):
    await seed_demo()
    async with get_sessionmaker()() as s:
        await _neha_lead(s, await _arjun(s))
    await client.delete("/api/v1/me", headers=ARTIST)
    items = (await client.get("/api/v1/leads/planner", headers=PLANNER)).json()["items"]
    gone = [i for i in items if i["artist"]["slug"] == ARJUN]
    assert gone and all(i["artist"]["name"] == "Artist no longer on Prasang" for i in gone)
