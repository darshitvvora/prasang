import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.service import get_own
from app.artists.views import to_media
from app.auth.deps import require_role
from app.auth.models import User
from app.contract import (
    CreateMediaLinkRequest,
    CreateMediaRequest,
    Media,
    MediaItems,
    MediaListResponse,
    ReorderMediaRequest,
    SetAvatarRequest,
    SetAvatarResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.db import get_session
from app.media import service
from app.media.storage import get_storage

log = logging.getLogger(__name__)
router = APIRouter(prefix="/artists/me", tags=["media"])
artist_only = require_role("artist")
JSON = {"response_model_by_alias": True}


@router.get("/media", response_model=MediaListResponse, **JSON)
async def list_media(user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    return await service.list_media(db, await get_own(db, user))


@router.post("/media/upload-url", response_model=UploadUrlResponse, **JSON)
async def upload_url(body: UploadUrlRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    artist = await get_own(db, user)
    return await service.upload_url(db, artist, body, get_storage())


@router.post("/media", response_model=Media, status_code=201, **JSON)
async def create_media(body: CreateMediaRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    artist = await get_own(db, user)
    if isinstance(body, CreateMediaLinkRequest):
        return to_media(await service.add_link(db, artist, body))
    return to_media(await service.add_upload(db, artist, body, get_storage()))


@router.post("/avatar", response_model=SetAvatarResponse, **JSON)
async def set_avatar(body: SetAvatarRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    artist = await get_own(db, user)
    return SetAvatarResponse(profile_image_url=await service.set_avatar(db, artist, body.storage_key, get_storage()))


@router.delete("/media/{media_id}", status_code=204)
async def delete_media(media_id: str, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    key = await service.delete_media(db, await get_own(db, user), media_id)
    if key:
        try:
            await get_storage().delete(key)
        except Exception:  # the row is gone; a leftover object only costs storage
            log.warning("could not delete %s from storage", key, exc_info=True)
    return Response(status_code=204)


@router.put("/media/order", response_model=MediaItems, **JSON)
async def reorder(body: ReorderMediaRequest, user: User = Depends(artist_only), db: AsyncSession = Depends(get_session)):
    items = await service.reorder(db, await get_own(db, user), body.ids)
    return MediaItems(items=[to_media(m) for m in items])
