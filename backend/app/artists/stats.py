"""Daily per-artist counters (profile views, contact clicks), bucketed by IST date."""
import uuid
from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistDailyStat

IST = timezone(timedelta(hours=5, minutes=30))


def today_ist(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(IST).date()


async def bump(session: AsyncSession, artist_id: uuid.UUID, field: str) -> None:
    stmt = insert(ArtistDailyStat).values(artist_id=artist_id, day=today_ist(), **{field: 1})
    stmt = stmt.on_conflict_do_update(
        index_elements=[ArtistDailyStat.artist_id, ArtistDailyStat.day],
        set_={field: getattr(ArtistDailyStat, field) + 1},
    )
    await session.execute(stmt)
    await session.commit()
