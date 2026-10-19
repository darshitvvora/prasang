from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.service import get_public
from app.auth.deps import require_role
from app.auth.models import User
from app.contract import CreateReviewRequest, ReviewPage, ReviewReplyRequest, ReviewReportRequest, UpdateReviewRequest
from app.contract import Review as ReviewOut
from app.db import get_session
from app.reviews import service

router = APIRouter(tags=["reviews"])
JSON = {"response_model_by_alias": True}


@router.get("/artists/{slug}/reviews", response_model=ReviewPage, **JSON)
async def reviews(slug: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50), db: AsyncSession = Depends(get_session)):
    return await service.public_reviews(db, await get_public(db, slug), page, size)


@router.get("/reviews/mine", response_model=ReviewPage, **JSON)
async def my_reviews(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50), user: User = Depends(require_role("artist")),
                     db: AsyncSession = Depends(get_session)):
    return await service.my_reviews(db, user, page, size)


@router.post("/reviews", response_model=ReviewOut, status_code=201, **JSON)
async def create_review(body: CreateReviewRequest, user: User = Depends(require_role("planner")), db: AsyncSession = Depends(get_session)):
    return await service.create_review(db, user, body)


@router.patch("/reviews/{review_id}", response_model=ReviewOut, **JSON)
async def update_review(review_id: str, body: UpdateReviewRequest, user: User = Depends(require_role("planner")),
                        db: AsyncSession = Depends(get_session)):
    return await service.update_review(db, user, review_id, body)


@router.put("/reviews/{review_id}/reply", response_model=ReviewOut, **JSON)
async def reply(review_id: str, body: ReviewReplyRequest, user: User = Depends(require_role("artist")),
                db: AsyncSession = Depends(get_session)):
    return await service.reply(db, user, review_id, body.text)


@router.post("/reviews/{review_id}/report", status_code=204)
async def report(review_id: str, body: ReviewReportRequest, user: User = Depends(require_role("artist")),
                 db: AsyncSession = Depends(get_session)):
    await service.report(db, user, review_id, body.reason)
    return Response(status_code=204)
