"""Serves shared profile links with preview tags baked in.

`GET /profile/{slug}` (outside /api/v1) returns the built web app's index.html with the artist's tags; production nginx
routes /profile/ here. `GET /api/v1/artists/{slug}/share-head` returns just the tags (used by the Vite dev server).
"""
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.service import get_public
from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.share.meta import inject, render_head, share_meta

page_router = APIRouter(tags=["share"])
api_router = APIRouter(tags=["share"])


@lru_cache(maxsize=4)
def _read_index(path: str, mtime: float) -> str:
    return Path(path).read_text(encoding="utf-8")


def _index(settings: Settings) -> str:
    if not settings.web_index_path or not Path(settings.web_index_path).is_file():
        raise AppError(503, "web_not_configured", "The web app is not available on this server")
    path = settings.web_index_path
    return _read_index(path, Path(path).stat().st_mtime)


@page_router.get("/profile/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def profile_page(slug: str, db: AsyncSession = Depends(get_session), settings: Settings = Depends(get_settings)):
    index = _index(settings)
    try:
        profile = await get_public(db, slug)
    except AppError:
        return HTMLResponse(index)  # the web app shows its own not-found page
    return HTMLResponse(inject(index, render_head(share_meta(profile, settings))))


@api_router.get("/artists/{slug}/share-head", response_class=HTMLResponse, include_in_schema=False)
async def share_head(slug: str, db: AsyncSession = Depends(get_session), settings: Settings = Depends(get_settings)):
    profile = await get_public(db, slug)
    return HTMLResponse(render_head(share_meta(profile, settings)))
