"""Who is calling: SuperTokens session (web cookies / mobile header) or, locally, a dev token."""
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.session.asyncio import get_session as get_st_session

from app.auth.models import User
from app.config import get_settings
from app.db import get_session
from app.errors import AppError, forbidden, unauthenticated

# Local-only shortcut (DEV_AUTH_HEADER=true): `Authorization: Bearer mock-…` acts as a demo user.
DEV_TOKENS = {"mock-artist": "dev-artist-arjun", "mock-planner": "dev-planner-neha", "mock-new": "dev-new-user"}
DEV_IDENTITY_EMAILS = {"dev-new-user": "new.user@gmail.com"}


@dataclass(frozen=True)
class AuthIdentity:
    user_id: str
    dev: bool = False


def _dev_token(request: Request) -> str | None:
    settings = get_settings()
    if not settings.dev_auth_header or settings.env == "production":
        return None
    auth = request.headers.get("authorization", "")
    return auth[7:] if auth.startswith("Bearer mock-") else None


async def current_identity(request: Request) -> AuthIdentity:
    token = _dev_token(request)
    if token is not None:
        user_id = DEV_TOKENS.get(token)
        if user_id is None:
            raise unauthenticated("Your session has expired. Please sign in again.")
        return AuthIdentity(user_id=user_id, dev=True)
    session = await get_st_session(request, session_required=False)
    if session is None:
        raise unauthenticated()
    return AuthIdentity(user_id=session.get_user_id())


async def current_user(identity: AuthIdentity = Depends(current_identity), db: AsyncSession = Depends(get_session)) -> User:
    user = await db.get(User, identity.user_id)
    if user is None:
        raise AppError(404, "profile_required", "Complete your profile to continue")
    if user.deleted_at is not None:
        raise unauthenticated("This account has been deleted.")
    if user.blocked_at is not None:
        raise AppError(403, "account_blocked", "This account has been blocked. Contact us if you think this is a mistake.")
    return user


def require_role(*roles: str):
    async def _dep(user: User = Depends(current_user)) -> User:
        if user.role != "admin" and user.role not in roles:
            raise forbidden()
        return user

    return _dep
