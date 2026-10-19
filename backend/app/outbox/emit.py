"""Write an outbox event in the caller's transaction; the projector picks it up after commit."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.outbox.models import OutboxEvent


def emit(session: AsyncSession, aggregate_type: str, aggregate_id: str, event_type: str, payload: dict | None = None) -> None:
    session.add(OutboxEvent(aggregate_type=aggregate_type, aggregate_id=str(aggregate_id), event_type=event_type, payload=payload or {}))


def artist_changed(session: AsyncSession, artist_id) -> None:
    emit(session, "artist", str(artist_id), "artist.upserted")
