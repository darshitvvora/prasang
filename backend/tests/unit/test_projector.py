"""Review Focus 2: Elasticsearch down → writes still succeed, outbox keeps the event, it is projected later."""
from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.db import get_sessionmaker
from app.outbox.emit import artist_changed
from app.outbox.models import OutboxEvent
from app.search.projector import project_batch
from tests.helpers import seed_demo


class FakeIndexer:
    def __init__(self, fail: bool = False):
        self.fail, self.upserts, self.deletes = fail, {}, []

    async def upsert(self, doc_id, doc):
        if self.fail:
            raise ConnectionError("elasticsearch is down")
        self.upserts[doc_id] = doc

    async def delete(self, doc_id):
        if self.fail:
            raise ConnectionError("elasticsearch is down")
        self.deletes.append(doc_id)


async def _emit_for(slug: str, published: bool = True) -> str:
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == slug))).scalar_one()
        artist.is_published = published
        artist_changed(s, artist.id)
        artist_changed(s, artist.id)  # duplicate events for one artist are coalesced
        await s.commit()
        return str(artist.id)


async def test_failed_indexing_keeps_events_for_retry():
    await seed_demo()
    artist_id = await _emit_for("dj-krish")
    assert await project_batch(get_sessionmaker(), FakeIndexer(fail=True)) == 0
    async with get_sessionmaker()() as s:
        events = (await s.execute(select(OutboxEvent))).scalars().all()
    assert all(e.processed_at is None and e.attempts == 1 and "down" in e.last_error for e in events)

    healthy = FakeIndexer()
    assert await project_batch(get_sessionmaker(), healthy) == 2
    assert healthy.upserts[artist_id]["slug"] == "dj-krish"
    async with get_sessionmaker()() as s:
        assert all(e.processed_at is not None for e in (await s.execute(select(OutboxEvent))).scalars())
    assert await project_batch(get_sessionmaker(), healthy) == 0


async def test_unpublished_artist_is_removed_from_index():
    await seed_demo()
    artist_id = await _emit_for("dj-krish", published=False)
    indexer = FakeIndexer()
    await project_batch(get_sessionmaker(), indexer)
    assert indexer.deletes == [artist_id]
