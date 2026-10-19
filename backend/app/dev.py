"""Local-only helpers (DEV_AUTH_HEADER=true, never production): reset the demo world for repeatable smoke tests."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import get_settings
from app.db import get_session, get_sessionmaker
from app.errors import not_found
from app.seed import DEV_NEW_USER_ID, seed

log = logging.getLogger(__name__)
router = APIRouter(tags=["dev"], include_in_schema=False)


@router.post("/_mock/reset")
async def reset(db: AsyncSession = Depends(get_session)):
    s = get_settings()
    if not s.dev_auth_header or s.env == "production":
        raise not_found("not_found", "Not found")
    await db.execute(text("TRUNCATE review_reports, reviews, leads, subscription_payments, subscriptions, payment_events, "
                          "outbox_events, artist_daily_stats, contact_messages"))
    await db.execute(delete(User).where(User.id == DEV_NEW_USER_ID))
    await db.commit()
    await seed(db, demo=True)
    try:
        from app.search.es import get_es
        from app.search.projector import reindex_all

        es = get_es()
        try:
            await reindex_all(get_sessionmaker(), es)
        finally:
            await es.close()
    except Exception:
        log.warning("reset: reindex failed (search may be stale)", exc_info=True)
    return {"ok": True}
