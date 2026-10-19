import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.auth.models import User
from app.contract import (
    ArtistLead,
    ArtistLeadsResponse,
    CreateLeadRequest,
    CreateLeadResponse,
    InquiryStatus,
    LeadArtistContact,
    LeadStatus,
    PlannerAnswerRequest,
    PlannerInquiriesResponse,
    PlannerInquiry,
    UpdateLeadRequest,
)
from app.db import get_session
from app.leads import service
from app.leads.booking import start_followup
from app.workflows.starter import get_starter

log = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])
JSON = {"response_model_by_alias": True}


@router.post("", response_model=CreateLeadResponse, status_code=201, **JSON)
async def create_lead(body: CreateLeadRequest, response: Response, user: User = Depends(require_role("planner")),
                      db: AsyncSession = Depends(get_session)):
    lead, created = await service.create_lead(db, user, body)
    artist = await service.artist_contact(db, lead)
    if created:
        try:
            await get_starter().start_lead_notification(str(lead.id))
            lead.notification_started_at = datetime.now(UTC)
            await db.commit()
        except Exception:  # the scheduler's sweep retries it; the planner must still get the contact (spec 5.5)
            log.exception("could not start notification workflow for lead %s", lead.id)
        await start_followup(db, lead)
    else:
        response.status_code = 200
    return CreateLeadResponse(lead_id=str(lead.id), artist=LeadArtistContact(
        name=artist.stage_name, contact_phone=artist.contact_phone, whatsapp_number=artist.whatsapp_number,
        instagram_handle=artist.instagram_handle))


@router.get("/artist", response_model=ArtistLeadsResponse, **JSON)
async def artist_leads(status: LeadStatus | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50),
                       user: User = Depends(require_role("artist")), db: AsyncSession = Depends(get_session)):
    return await service.artist_leads(db, user, status, page, size)


@router.get("/planner", response_model=PlannerInquiriesResponse, **JSON)
async def planner_inquiries(status: InquiryStatus | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=50),
                            user: User = Depends(require_role("planner")), db: AsyncSession = Depends(get_session)):
    return await service.planner_inquiries(db, user, status, page, size)


@router.patch("/{lead_id}/planner-answer", response_model=PlannerInquiry, **JSON)
async def planner_answer(lead_id: str, body: PlannerAnswerRequest, user: User = Depends(require_role("planner")),
                         db: AsyncSession = Depends(get_session)):
    return await service.planner_answer(db, user, lead_id, body.answer)


@router.patch("/{lead_id}", response_model=ArtistLead, **JSON)
async def update_lead(lead_id: str, body: UpdateLeadRequest, user: User = Depends(require_role("artist")),
                      db: AsyncSession = Depends(get_session)):
    return await service.update_status(db, user, lead_id, body.status)
