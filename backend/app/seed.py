"""Seed data. Always: localities + subscription plans. demo=True: demo users, 12 artists, media, reviews, leads.

Datasets are shared with the Mockoon mock (mockoon/data) and the contract examples so the mock and the real
API serve the same demo world. Ids are deterministic (uuid5), so seeding is idempotent via session.merge.
"""
import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.auth.models import User
from app.config import get_settings
from app.leads.budgets import BUDGETS, budget_key_for
from app.leads.models import Lead
from app.locations.models import Locality
from app.media.models import ArtistMedia
from app.reviews.models import Review
from app.subscriptions.models import SubscriptionPlan

NS = uuid.UUID("6f1c2b8e-5d4a-4c3b-9a21-7e0f3d5b8c10")
DEV_ARTIST_ID = "dev-artist-arjun"
DEV_PLANNER_ID = "dev-planner-neha"
DEV_NEW_USER_ID = "dev-new-user"

PLAN_EXTRAS = {  # not shown on the pricing page but drive ranking/notifications
    "free": {"search_boost_score": 0, "is_featured": False, "whatsapp_notifications": False},
    "basic": {"search_boost_score": 10, "is_featured": False, "whatsapp_notifications": True},
    "pro": {"search_boost_score": 25, "is_featured": True, "whatsapp_notifications": True},
    "premium": {"search_boost_score": 50, "is_featured": True, "whatsapp_notifications": True},
}
INQUIRY_TO_LEAD_STATUS = {"pending": "new", "responded": "contacted", "confirmed": "converted", "declined": "declined"}


def sid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NS, f"{kind}:{key}")


def _load(rel: str):
    return json.loads((Path(get_settings().seed_root) / rel).read_text())


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def seed(session: AsyncSession, *, demo: bool) -> None:
    await _seed_localities(session)
    await _seed_plans(session)
    if demo:
        await _seed_demo(session)
    await session.commit()


async def _seed_localities(session: AsyncSession) -> None:
    for i, city in enumerate(_load("mockoon/data/locations.json")["cities"]):
        await session.merge(Locality(id=sid("city", city["name"]), city=city["name"], area=None, sort_order=i))
        for j, area in enumerate(city["areas"]):
            await session.merge(Locality(id=sid("area", f"{city['name']}/{area}"), city=city["name"], area=area, sort_order=j))


async def _seed_plans(session: AsyncSession) -> None:
    for i, p in enumerate(_load("contracts/examples/subscriptions/plans.response.json")["items"]):
        await session.merge(SubscriptionPlan(
            tier=p["tier"], name=p["name"], tagline=p["tagline"], monthly_price=p["monthlyPrice"], annual_price=p["annualPrice"],
            annual_monthly_equivalent=p["annualMonthlyEquivalent"], lead_limit_monthly=p["leadLimitMonthly"],
            max_images=p["maxImages"], max_videos=p["maxVideos"], popular=p["popular"], features=p["features"],
            sort_order=i, **PLAN_EXTRAS[p["tier"]],
        ))


async def _user(session: AsyncSession, user_id: str, name: str, role: str, email: str | None = None, phone: str | None = None) -> None:
    await session.merge(User(id=user_id, full_name=name, role=role, email=email, phone=phone))


async def _seed_demo(session: AsyncSession) -> None:
    await _user(session, DEV_ARTIST_ID, "Arjun Malhotra", "artist", "arjun.malhotra@gmail.com", "9820011001")
    await _user(session, DEV_PLANNER_ID, "Neha Kulkarni", "planner", "neha.kulkarni@gmail.com", "9920012345")

    artist_ids: dict[str, uuid.UUID] = {}
    for n, a in enumerate(_load("mockoon/data/artists.json"), start=1):
        owner = DEV_ARTIST_ID if a["artistId"] == "art-001" else f"demo-artist-{n:03d}"
        if owner != DEV_ARTIST_ID:
            await _user(session, owner, a["name"], "artist")
        artist_id = sid("artist", a["artistId"])
        artist_ids[a["artistId"]] = artist_id
        tier = a["subscriptionTier"]
        await session.merge(ArtistProfile(
            id=artist_id, user_id=owner, slug=a["slug"], stage_name=a["name"], artist_type=a["artistType"], bio=a["bio"],
            location_city=a["locationCity"], location_area=a["locationArea"], per_event_rate_min=a["perEventRateMin"],
            per_event_rate_max=a["perEventRateMax"], experience_years=a["experienceYears"],
            event_types_supported=a["eventTypesSupported"], languages_spoken=a["languagesSpoken"], ready_to_travel=a["readyToTravel"],
            instagram_handle=a["instagramHandle"], youtube_channel=a["youtubeChannel"], facebook_url=a.get("facebookUrl"),
            profile_image_url=a["profileImageUrl"], contact_phone=a["contactPhone"], whatsapp_number=a["whatsappNumber"],
            is_published=True, is_verified=a["isVerified"], is_featured=a["isFeatured"], subscription_tier=tier,
            tier_source="free" if tier == "free" else "paid", search_boost_score=PLAN_EXTRAS[tier]["search_boost_score"],
            average_rating=a["averageRating"], total_reviews=a["totalReviews"],
            media=[ArtistMedia(id=sid("media", m["id"]), kind=m["kind"], url=m["url"], embed_url=m.get("embedUrl"),
                               thumbnail_url=m["thumbnailUrl"], caption=m["caption"], display_order=m["displayOrder"])
                   for m in a["media"]],
        ))
        for r in _load("mockoon/data/reviews.json"):
            await session.merge(Review(
                id=sid("review", f"{a['artistId']}/{r['id']}"), artist_id=artist_id, reviewer_name=r["reviewerName"],
                rating=r["rating"], event_type=r["eventType"], event_month=r["eventMonth"], text=r["text"], created_at=_ts(r["createdAt"]),
            ))

    await _seed_artist_leads(session, artist_ids["art-001"])
    await _seed_planner_inquiries(session, artist_ids)


async def _seed_artist_leads(session: AsyncSession, artist_id: uuid.UUID) -> None:
    """Arjun's leads, shifted so the newest lands 'now' (keeps them in the current month for quota display)."""
    items = _load("mockoon/data/artist-leads.json")["items"]
    newest = max(_ts(i["createdAt"]) for i in items)
    shift = datetime.now(UTC) - newest
    for item in items:
        planner_id = "demo-planner-" + item["plannerName"].lower().replace(" ", "-")
        await _user(session, planner_id, item["plannerName"], "planner", item["plannerEmail"], item["plannerPhone"])
        budget = budget_key_for(item["budgetMin"])
        await session.merge(Lead(
            id=sid("lead", item["id"]), artist_id=artist_id, planner_id=planner_id, planner_name=item["plannerName"],
            planner_phone=item["plannerPhone"] or "9000000000", planner_email=item["plannerEmail"], event_type=item["eventType"],
            event_date=date.fromisoformat(item["eventDate"]) if item["eventDate"] else None, event_city=item["eventCity"],
            budget_range=budget, budget_min=BUDGETS[budget][0], budget_max=BUDGETS[budget][1], notes=item["notes"],
            source="profile", status=item["status"], is_locked=item["isLocked"],
            created_at=_ts(item["createdAt"]) + shift, notification_started_at=_ts(item["createdAt"]) + shift,
        ))


async def _seed_planner_inquiries(session: AsyncSession, artist_ids: dict[str, uuid.UUID]) -> None:
    for item in _load("mockoon/data/planner-inquiries.json")["items"]:
        budget = budget_key_for(item["budgetMin"])
        await session.merge(Lead(
            id=sid("lead", item["id"]), artist_id=artist_ids[item["artist"]["artistId"]], planner_id=DEV_PLANNER_ID,
            planner_name="Neha Kulkarni", planner_phone="9920012345", planner_email="neha.kulkarni@gmail.com",
            event_type=item["eventType"], event_date=date.fromisoformat(item["eventDate"]) if item["eventDate"] else None,
            event_city="Mumbai", budget_range=budget, budget_min=BUDGETS[budget][0], budget_max=BUDGETS[budget][1],
            notes=item["notes"], source="search", status=INQUIRY_TO_LEAD_STATUS[item["status"]], is_locked=False,
            created_at=_ts(item["contactedAt"]), notification_started_at=_ts(item["contactedAt"]),
        ))
