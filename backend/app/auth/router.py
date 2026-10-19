"""/me (Prasang profile of the signed-in user) and /auth/providers."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.asyncio import get_user as get_st_user

from app.artists.models import ArtistProfile
from app.auth.deps import DEV_IDENTITY_EMAILS, AuthIdentity, current_identity, current_user
from app.auth.models import User
from app.auth.supertokens_setup import google_enabled
from app.config import get_settings
from app.contract import AuthProvidersResponse, CreateMeRequest, Me, UpdateMeRequest
from app.db import get_session
from app.errors import conflict, validation

router = APIRouter()


async def to_me(db: AsyncSession, user: User) -> Me:
    slug = (await db.execute(select(ArtistProfile.slug).where(ArtistProfile.user_id == user.id))).scalar_one_or_none()
    return Me(id=user.id, email=user.email, full_name=user.full_name, phone=user.phone, role=user.role,
              avatar_url=user.avatar_url, artist_slug=slug, created_at=user.created_at)


async def _login_contact(identity: AuthIdentity) -> tuple[str | None, str | None]:
    """Email / 10-digit phone the user signed in with (Google email or OTP phone)."""
    if identity.dev:
        return DEV_IDENTITY_EMAILS.get(identity.user_id), None
    st_user = await get_st_user(identity.user_id)
    if st_user is None:
        return None, None
    email = st_user.emails[0] if st_user.emails else None
    phone = st_user.phone_numbers[0] if st_user.phone_numbers else None
    if phone and phone.startswith("+91"):
        phone = phone[3:]
    return email, phone


@router.get("/auth/providers", response_model=AuthProvidersResponse, response_model_by_alias=True)
async def providers():
    return AuthProvidersResponse(google=google_enabled(get_settings()), phone_otp=True)


@router.get("/me", response_model=Me, response_model_by_alias=True)
async def get_me(user: User = Depends(current_user), db: AsyncSession = Depends(get_session)):
    return await to_me(db, user)


@router.post("/me", response_model=Me, response_model_by_alias=True, status_code=201)
async def create_me(body: CreateMeRequest, identity: AuthIdentity = Depends(current_identity), db: AsyncSession = Depends(get_session)):
    if body.role == "admin":
        raise validation({"role": "Choose artist or planner"})
    if await db.get(User, identity.user_id) is not None:
        raise conflict("profile_exists", "Your profile already exists")
    email, login_phone = await _login_contact(identity)
    user = User(id=identity.user_id, role=body.role, full_name=body.full_name.strip(), email=email, phone=body.phone or login_phone)
    db.add(user)
    await db.commit()
    return await to_me(db, user)


@router.patch("/me", response_model=Me, response_model_by_alias=True)
async def update_me(body: UpdateMeRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)):
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.phone is not None:
        user.phone = body.phone
    await db.commit()
    return await to_me(db, user)
