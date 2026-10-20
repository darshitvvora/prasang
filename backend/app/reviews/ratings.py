from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artists.models import ArtistProfile
from app.outbox.emit import artist_changed
from app.reviews.models import Review


async def recalc_rating(session: AsyncSession, artist_id) -> None:
    """Average and count over visible reviews; the caller commits."""
    avg, count = (await session.execute(select(func.avg(Review.rating), func.count()).where(
        Review.artist_id == artist_id, Review.hidden_at.is_(None)))).one()
    artist = await session.get(ArtistProfile, artist_id)
    artist.average_rating = round(float(avg), 2) if count else 0
    artist.total_reviews = count
    artist_changed(session, artist_id)
