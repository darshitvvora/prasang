"""Verified reviews: a planner reviews a confirmed booking after the event; the artist can reply once and report."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.artists.service import get_own
from app.artists.stats import IST, today_ist
from app.auth.models import User
from app.contract import CreateReviewRequest, ReviewPage, UpdateReviewRequest
from app.contract import Review as ReviewOut
from app.errors import AppError, conflict, not_found
from app.leads.models import Lead
from app.leads.service import can_review
from app.reviews.models import Review, ReviewReport
from app.reviews.ratings import recalc_rating

EDIT_WINDOW = timedelta(days=7)


def to_review(r: Review) -> ReviewOut:
    return ReviewOut(id=str(r.id), reviewer_name=r.reviewer_name, rating=r.rating, event_type=r.event_type,
                     event_month=r.event_month, text=r.text, created_at=r.created_at, verified=r.lead_id is not None,
                     artist_reply=r.artist_reply)


def reviewer_name(full_name: str) -> str:
    parts = full_name.split()
    if not parts:
        return "Prasang user"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0].upper()}."


def _uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def create_review(session: AsyncSession, planner: User, body: CreateReviewRequest) -> ReviewOut:
    lid = _uuid(body.lead_id)
    lead = await session.get(Lead, lid, with_for_update=True) if lid else None
    if lead is None or lead.planner_id != planner.id:
        raise not_found("lead_not_found", "That inquiry doesn't exist")
    if not can_review(lead, today_ist()):
        raise AppError(403, "review_not_allowed", "You can review an artist after a confirmed booking, once the event is over")
    if (await session.execute(select(Review.id).where(Review.lead_id == lead.id))).first():
        raise conflict("review_exists", "You've already reviewed this booking")
    month = lead.event_date.strftime("%Y-%m") if lead.event_date else lead.created_at.astimezone(IST).strftime("%Y-%m")
    review = Review(artist_id=lead.artist_id, lead_id=lead.id, planner_id=planner.id, reviewer_name=reviewer_name(planner.full_name),
                    rating=body.rating, event_type=lead.event_type, event_month=month, text=body.text.strip())
    session.add(review)
    await session.flush()
    await recalc_rating(session, lead.artist_id)
    await session.commit()
    return to_review(review)


async def _authored(session: AsyncSession, planner: User, review_id: str) -> Review:
    rid = _uuid(review_id)
    review = await session.get(Review, rid) if rid else None
    if review is None or review.planner_id != planner.id:
        raise not_found("review_not_found", "That review doesn't exist")
    return review


async def update_review(session: AsyncSession, planner: User, review_id: str, body: UpdateReviewRequest) -> ReviewOut:
    review = await _authored(session, planner, review_id)
    if datetime.now(UTC) - review.created_at > EDIT_WINDOW:
        raise conflict("review_locked", "Reviews can be edited for 7 days after posting")
    if body.rating is not None:
        review.rating = body.rating
    if body.text is not None:
        review.text = body.text.strip()
    await session.flush()
    await recalc_rating(session, review.artist_id)
    await session.commit()
    return to_review(review)


async def _about_me(session: AsyncSession, artist_user: User, review_id: str) -> Review:
    artist = await get_own(session, artist_user)
    rid = _uuid(review_id)
    review = await session.get(Review, rid) if rid else None
    if review is None or review.artist_id != artist.id:
        raise not_found("review_not_found", "That review doesn't exist")
    return review


async def reply(session: AsyncSession, artist_user: User, review_id: str, text: str) -> ReviewOut:
    review = await _about_me(session, artist_user, review_id)
    review.artist_reply, review.artist_replied_at = text.strip(), datetime.now(UTC)
    await session.commit()
    return to_review(review)


async def report(session: AsyncSession, artist_user: User, review_id: str, reason: str) -> None:
    review = await _about_me(session, artist_user, review_id)
    exists = (await session.execute(select(ReviewReport.id).where(
        ReviewReport.review_id == review.id, ReviewReport.status == "open"))).first()
    if not exists:
        session.add(ReviewReport(review_id=review.id, reason=reason.strip()))
        await session.commit()


async def _page(session: AsyncSession, where, page: int, size: int) -> ReviewPage:
    total = (await session.execute(select(func.count()).select_from(Review).where(where))).scalar_one()
    rows = (await session.execute(select(Review).where(where).order_by(Review.created_at.desc())
                                  .offset((page - 1) * size).limit(size))).scalars()
    return ReviewPage(items=[to_review(r) for r in rows], total=total, page=page, size=size)


async def public_reviews(session: AsyncSession, artist: ArtistProfile, page: int, size: int) -> ReviewPage:
    return await _page(session, (Review.artist_id == artist.id) & Review.hidden_at.is_(None), page, size)


async def my_reviews(session: AsyncSession, artist_user: User, page: int, size: int) -> ReviewPage:
    artist = await get_own(session, artist_user)
    return await _page(session, (Review.artist_id == artist.id) & Review.hidden_at.is_(None), page, size)
