"""Artist profile use-cases. Every write emits an outbox event in the same transaction (→ Elasticsearch)."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.completeness import completeness
from app.artists.models import ArtistDailyStat, ArtistProfile
from app.artists.slugs import unique_slug
from app.artists.views import to_profile
from app.artists.visibility import public_filter
from app.auth.models import User
from app.config import get_settings
from app.contract import ArtistDashboard, ArtistProfileInput, ArtistProfilePatch, DashboardMetrics, LeadSourceStat, Metric, RatingMetric
from app.embeds import normalize_facebook_url, normalize_instagram_handle, parse_youtube_channel, resolve_youtube_channel_id
from app.errors import AppError, conflict, not_found, validation
from app.labels import LEAD_SOURCE_LABELS
from app.leads.models import Lead
from app.leads.usage import month_bounds_ist, plan_usage, previous_month_bounds_ist
from app.leads.views import to_artist_lead
from app.outbox.emit import artist_changed
from app.reviews.models import Review
from app.subscriptions.models import Subscription, SubscriptionPlan

PROFILE_FIELDS = {
    "name": "stage_name", "artist_type": "artist_type", "location_city": "location_city", "location_area": "location_area",
    "bio": "bio", "experience_years": "experience_years", "per_event_rate_min": "per_event_rate_min",
    "per_event_rate_max": "per_event_rate_max", "event_types_supported": "event_types_supported",
    "languages_spoken": "languages_spoken", "ready_to_travel": "ready_to_travel", "contact_phone": "contact_phone",
    "whatsapp_number": "whatsapp_number", "is_published": "is_published",
}


async def _apply_socials(profile: ArtistProfile, changes: dict) -> None:
    """Validate/normalise social links; resolve the YouTube channel id for the channel widget when possible."""
    if "instagram_handle" in changes:
        raw = changes["instagram_handle"]
        profile.instagram_handle = normalize_instagram_handle(raw) if raw else None
    if "facebook_url" in changes:
        raw = changes["facebook_url"]
        profile.facebook_url = normalize_facebook_url(raw) if raw else None
    if "youtube_channel" in changes:
        raw = (changes["youtube_channel"] or "").strip()
        if not raw:
            profile.youtube_channel, profile.youtube_channel_id = None, None
        else:
            channel_id, handle = parse_youtube_channel(raw)
            profile.youtube_channel = channel_id or handle
            profile.youtube_channel_id = channel_id or await resolve_youtube_channel_id(handle, get_settings().youtube_api_key)


def _check_rates(profile: ArtistProfile) -> None:
    if profile.per_event_rate_max < profile.per_event_rate_min:
        raise validation({"perEventRateMax": "Top rate must be at least the starting rate"})


async def counts(session: AsyncSession, artist_id) -> tuple[int, int]:
    media = len((await session.get(ArtistProfile, artist_id)).media)
    reviews = (await session.execute(select(func.count()).select_from(Review).where(Review.artist_id == artist_id))).scalar_one()
    return media, reviews


async def profile_response(session: AsyncSession, profile: ArtistProfile):
    media, reviews = await counts(session, profile.id)
    return to_profile(profile, completeness(profile, media, reviews))


async def get_own(session: AsyncSession, user: User) -> ArtistProfile:
    profile = (await session.execute(select(ArtistProfile).where(ArtistProfile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        raise not_found("artist_profile_not_found", "Create your artist profile to continue")
    return profile


async def get_public(session: AsyncSession, slug: str) -> ArtistProfile:
    profile = (await session.execute(
        select(ArtistProfile).where(ArtistProfile.slug == slug, public_filter()))).scalar_one_or_none()
    if profile is None:
        raise not_found("artist_not_found", "No artist found for this link")
    return profile


async def create_profile(session: AsyncSession, user: User, data: ArtistProfileInput) -> ArtistProfile:
    if (await session.execute(select(ArtistProfile.id).where(ArtistProfile.user_id == user.id))).first():
        raise conflict("artist_exists", "You already have an artist profile")
    values = data.model_dump()
    profile = ArtistProfile(user_id=user.id, slug=await unique_slug(session, data.name), subscription_tier="free", tier_source="free",
                            is_published=False, media=[], **{col: values[f] for f, col in PROFILE_FIELDS.items() if f in values})
    await _apply_socials(profile, values)
    _check_rates(profile)
    session.add(profile)
    await session.flush()
    artist_changed(session, profile.id)
    await session.commit()
    return profile


async def update_profile(session: AsyncSession, user: User, patch: ArtistProfilePatch) -> ArtistProfile:
    profile = await get_own(session, user)
    changes = patch.model_dump(exclude_unset=True)
    for field, col in PROFILE_FIELDS.items():
        if field in changes:
            if changes[field] is None and field not in ("whatsapp_number",):
                raise validation({_camel(field): "This field can't be empty"})
            setattr(profile, col, changes[field])
    await _apply_socials(profile, changes)
    _check_rates(profile)
    artist_changed(session, profile.id)
    await session.commit()
    return profile


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(w.title() for w in rest)


# ---------- dashboard ----------

def _change(this: int, last: int) -> int | None:
    return None if last == 0 else round((this - last) * 100 / last)


async def _stat_sum(session, artist_id, column, start, end) -> int:
    from app.artists.stats import IST
    day_from, day_to = start.astimezone(IST).date(), end.astimezone(IST).date()
    q = select(func.coalesce(func.sum(column), 0)).where(
        ArtistDailyStat.artist_id == artist_id, ArtistDailyStat.day >= day_from, ArtistDailyStat.day < day_to)
    return (await session.execute(q)).scalar_one()


async def _lead_count(session, artist_id, start, end) -> int:
    q = select(func.count()).select_from(Lead).where(Lead.artist_id == artist_id, Lead.created_at >= start, Lead.created_at < end)
    return (await session.execute(q)).scalar_one()


async def usage_for(session: AsyncSession, profile: ArtistProfile, now: datetime):
    plan = await session.get(SubscriptionPlan, profile.subscription_tier)
    start, end = month_bounds_ist(now)
    sub = (await session.execute(select(Subscription).where(
        Subscription.artist_id == profile.id, Subscription.status.in_(("active", "halted"))))).scalar_one_or_none()
    return plan_usage(profile, plan, await _lead_count(session, profile.id, start, end), now, sub)


async def dashboard(session: AsyncSession, user: User, now: datetime | None = None) -> ArtistDashboard:
    now = now or datetime.now(UTC)
    profile = await get_own(session, user)
    this_start, this_end = month_bounds_ist(now)
    last_start, last_end = previous_month_bounds_ist(now)

    async def metric(column) -> Metric:
        this = await _stat_sum(session, profile.id, column, this_start, this_end)
        return Metric(value=this, change_pct=_change(this, await _stat_sum(session, profile.id, column, last_start, last_end)))

    leads_this = await _lead_count(session, profile.id, this_start, this_end)
    leads_last = await _lead_count(session, profile.id, last_start, last_end)
    recent = (await session.execute(select(Lead).where(Lead.artist_id == profile.id).order_by(Lead.created_at.desc()).limit(3))).scalars()

    since = now - timedelta(days=30)
    by_source = dict((await session.execute(select(Lead.source, func.count()).where(
        Lead.artist_id == profile.id, Lead.created_at >= since).group_by(Lead.source))).all())
    total = sum(by_source.values())
    sources = [LeadSourceStat(source=s, label=label, pct=round(100 * by_source.get(s, 0) / total) if total else 0)
               for s, label in LEAD_SOURCE_LABELS.items()]

    media, reviews = await counts(session, profile.id)
    return ArtistDashboard(
        greeting_name=user.full_name.split(" ")[0], is_published=profile.is_published,
        plan=await usage_for(session, profile, now),
        metrics=DashboardMetrics(
            profile_views=await metric(ArtistDailyStat.profile_views),
            contact_clicks=await metric(ArtistDailyStat.contact_clicks),
            leads_this_month=Metric(value=leads_this, change_pct=_change(leads_this, leads_last)),
            average_rating=RatingMetric(value=float(profile.average_rating or 0), total_reviews=profile.total_reviews),
        ),
        recent_leads=[to_artist_lead(lead) for lead in recent],
        lead_sources=sources,
        completeness=completeness(profile, media, reviews),
    )


__all__ = ["AppError", "create_profile", "update_profile", "get_own", "get_public", "dashboard", "profile_response", "usage_for"]
