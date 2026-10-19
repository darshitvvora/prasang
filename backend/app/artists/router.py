from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists import service
from app.artists.stats import bump
from app.artists.views import to_detail
from app.auth.deps import require_role
from app.auth.models import User
from app.contract import ArtistDashboard, ArtistDetail, ArtistProfile, ArtistProfileInput, ArtistProfilePatch
from app.db import get_session

router = APIRouter(tags=["artists"])
artist_only = require_role("artist")
JSON = {"response_model_by_alias": True}


@router.post("/artists", response_model=ArtistProfile, status_code=201, **JSON)
async def create_artist(body: ArtistProfileInput, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.profile_response(db, await service.create_profile(db, user, body))


@router.get("/artists/me", response_model=ArtistProfile, **JSON)
async def my_artist(user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.profile_response(db, await service.get_own(db, user))


@router.patch("/artists/me", response_model=ArtistProfile, **JSON)
async def update_artist(body: ArtistProfilePatch, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.profile_response(db, await service.update_profile(db, user, body))


@router.get("/artists/me/dashboard", response_model=ArtistDashboard, **JSON)
async def artist_dashboard(user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.dashboard(db, user)


@router.get("/artists/{slug}", response_model=ArtistDetail, **JSON)
async def public_artist(slug: str, db: AsyncSession = Depends(get_session)):
    profile = await service.get_public(db, slug)
    detail = to_detail(profile)
    await bump(db, profile.id, "profile_views")
    return detail


@router.post("/artists/{slug}/contact-click", status_code=204)
async def contact_click(slug: str, db: AsyncSession = Depends(get_session)):
    profile = await service.get_public(db, slug)
    await bump(db, profile.id, "contact_clicks")
    return Response(status_code=204)
