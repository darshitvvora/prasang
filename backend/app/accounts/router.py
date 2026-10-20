"""DELETE /me — self-serve account deletion. Needs a sign-in from the last 10 minutes (re-enter the OTP / Google)."""
import logging
import time

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.session.asyncio import get_session as get_st_session
from supertokens_python.recipe.session.asyncio import get_session_information

from app.accounts.deletion import delete_account
from app.auth.deps import AuthIdentity, current_identity, current_user
from app.auth.models import User
from app.auth.router import login_contact
from app.db import get_session
from app.errors import AppError

log = logging.getLogger(__name__)
router = APIRouter(tags=["accounts"])
FRESH_SECONDS = 10 * 60


async def session_age_seconds(request: Request, identity: AuthIdentity = Depends(current_identity)) -> float:
    if identity.dev:
        return 0
    session = await get_st_session(request, session_required=False)
    info = await get_session_information(session.get_handle()) if session else None
    if info is None:
        return float("inf")
    return time.time() - info.time_created / 1000


@router.delete("/me", status_code=204)
async def delete_me(identity: AuthIdentity = Depends(current_identity), user: User = Depends(current_user),
                    age: float = Depends(session_age_seconds), db: AsyncSession = Depends(get_session)):
    if age > FRESH_SECONDS:
        email, phone = await login_contact(identity)
        details = {"method": "phone", "phone": phone} if phone else {"method": "google", "email": email}
        raise AppError(403, "reauth_required", "Please confirm it's you by signing in again", details)
    await delete_account(db, user)
    if not identity.dev:
        try:
            from supertokens_python.asyncio import delete_user

            await delete_user(identity.user_id)  # also ends every session
        except Exception:
            log.exception("could not delete SuperTokens user %s (the Prasang account is already deleted)", identity.user_id)
    return Response(status_code=204)
