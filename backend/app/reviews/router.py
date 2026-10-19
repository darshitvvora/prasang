from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.service import get_public
from app.contract import Review as ReviewOut
from app.contract import ReviewPage
from app.db import get_session
from app.reviews.models import Review

router = APIRouter(tags=["reviews"])


@router.get("/artists/{slug}/reviews", response_model=ReviewPage, response_model_by_alias=True)
async def reviews(slug: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50), db: AsyncSession = Depends(get_session)):
    artist = await get_public(db, slug)
    where = Review.artist_id == artist.id
    total = (await db.execute(select(func.count()).select_from(Review).where(where))).scalar_one()
    query = select(Review).where(where).order_by(Review.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(query)).scalars()
    items = [ReviewOut(id=str(r.id), reviewer_name=r.reviewer_name, rating=r.rating, event_type=r.event_type,
                       event_month=r.event_month, text=r.text, created_at=r.created_at) for r in rows]
    return ReviewPage(items=items, total=total, page=page, size=size)
