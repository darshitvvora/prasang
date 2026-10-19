"""Outbox → Elasticsearch projector, plus full reindex with an atomic alias swap."""
import asyncio
import logging
from datetime import UTC, datetime
from typing import Protocol

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.artists.models import ArtistProfile
from app.outbox.models import OutboxEvent
from app.search.documents import artist_document
from app.search.es import alias, get_es
from app.search.mapping import INDEX_BODY

log = logging.getLogger(__name__)


class Indexer(Protocol):
    async def upsert(self, doc_id: str, doc: dict) -> None: ...
    async def delete(self, doc_id: str) -> None: ...


class EsIndexer:
    def __init__(self, es: AsyncElasticsearch, refresh: bool = False):
        self.es, self.refresh = es, refresh

    async def upsert(self, doc_id: str, doc: dict) -> None:
        await self.es.index(index=alias(), id=doc_id, document=doc, refresh="wait_for" if self.refresh else False)

    async def delete(self, doc_id: str) -> None:
        try:
            await self.es.delete(index=alias(), id=doc_id, refresh="wait_for" if self.refresh else False)
        except NotFoundError:
            pass


async def project_batch(sessions: async_sessionmaker[AsyncSession], indexer: Indexer, batch_size: int = 100) -> int:
    """Project up to batch_size pending events. Returns how many events were marked processed."""
    async with sessions() as session, session.begin():
        events = (await session.execute(
            select(OutboxEvent).where(OutboxEvent.processed_at.is_(None)).order_by(OutboxEvent.id)
            .limit(batch_size).with_for_update(skip_locked=True))).scalars().all()
        by_artist: dict[str, list[OutboxEvent]] = {}
        for event in events:
            if event.aggregate_type == "artist":
                by_artist.setdefault(event.aggregate_id, []).append(event)
        processed = 0
        now = datetime.now(UTC)
        for artist_id, group in by_artist.items():
            try:
                profile = await session.get(ArtistProfile, artist_id)
                if profile is not None and profile.is_published:
                    await indexer.upsert(artist_id, artist_document(profile))
                else:
                    await indexer.delete(artist_id)
            except Exception as exc:  # keep events for the next tick
                log.warning("projecting artist %s failed: %s", artist_id, exc)
                for event in group:
                    event.attempts += 1
                    event.last_error = str(exc)[:1000]
                continue
            for event in group:
                event.processed_at = now
            processed += len(group)
    return processed


async def ensure_index(es: AsyncElasticsearch) -> None:
    if not await es.indices.exists_alias(name=alias()):
        name = f"{alias()}_v{datetime.now(UTC):%Y%m%d%H%M%S%f}"
        await es.indices.create(index=name, body=INDEX_BODY)
        await es.indices.put_alias(index=name, name=alias())


async def reindex_all(sessions: async_sessionmaker[AsyncSession], es: AsyncElasticsearch) -> int:
    """Build a fresh index from Postgres and atomically point the alias at it."""
    name = f"{alias()}_v{datetime.now(UTC):%Y%m%d%H%M%S%f}"
    await es.indices.create(index=name, body=INDEX_BODY)
    async with sessions() as session:
        profiles = (await session.execute(select(ArtistProfile).where(ArtistProfile.is_published.is_(True)))).scalars().all()
        actions = [{"_index": name, "_id": str(p.id), "_source": artist_document(p)} for p in profiles]
    await async_bulk(es, actions)
    await es.indices.refresh(index=name)
    old = list((await es.indices.get_alias(name=alias())).keys()) if await es.indices.exists_alias(name=alias()) else []
    swap = [{"remove": {"index": i, "alias": alias()}} for i in old] + [{"add": {"index": name, "alias": alias()}}]
    await es.indices.update_aliases(actions=swap)
    for index in old:
        await es.indices.delete(index=index)
    return len(actions)


async def run_projector(sessions: async_sessionmaker[AsyncSession], poll_seconds: float = 1.0) -> None:
    es = get_es()
    await ensure_index(es)
    indexer = EsIndexer(es)
    log.info("projector started (alias %s)", alias())
    while True:
        try:
            if await project_batch(sessions, indexer):
                continue  # drain backlog without sleeping
        except Exception:
            log.exception("projector tick failed")
        await asyncio.sleep(poll_seconds)
