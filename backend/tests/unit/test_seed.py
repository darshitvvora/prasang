import os
import subprocess
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.artists.models import ArtistProfile
from app.db import Base, get_sessionmaker
from app.leads.models import Lead
from app.locations.models import Locality
from app.seed import DEV_ARTIST_ID, DEV_PLANNER_ID, seed
from app.subscriptions.models import SubscriptionPlan

BACKEND = Path(__file__).resolve().parents[2]


async def _count(session, stmt) -> int:
    return (await session.execute(stmt)).scalar_one()


async def test_demo_seed_is_complete_and_idempotent():
    async with get_sessionmaker()() as session:
        await seed(session, demo=True)
        await seed(session, demo=True)

        assert await _count(session, select(func.count()).select_from(ArtistProfile)) == 12
        assert await _count(session, select(func.count()).select_from(SubscriptionPlan)) == 4
        mumbai_areas = select(func.count()).select_from(Locality).where(Locality.city == "Mumbai", Locality.area.is_not(None))
        mumbai = await _count(session, mumbai_areas)
        assert mumbai == 8

        arjun = (await session.execute(select(ArtistProfile).where(ArtistProfile.user_id == DEV_ARTIST_ID))).scalar_one()
        assert (arjun.slug, arjun.subscription_tier, arjun.is_published) == ("arjun-malhotra-magic", "basic", True)
        arjun_leads = (await session.execute(select(Lead).where(Lead.artist_id == arjun.id))).scalars().all()
        assert len(arjun_leads) == 8  # 7 from his dataset + Neha's inquiry to him
        assert sum(lead.is_locked for lead in arjun_leads) == 1

        neha_leads = await _count(session, select(func.count()).select_from(Lead).where(Lead.planner_id == DEV_PLANNER_ID))
        assert neha_leads == 5


async def test_base_seed_has_no_demo_data():
    async with get_sessionmaker()() as session:
        await seed(session, demo=False)
        assert await _count(session, select(func.count()).select_from(ArtistProfile)) == 0
        assert await _count(session, select(func.count()).select_from(SubscriptionPlan)) == 4


async def test_alembic_migration_matches_models():
    """Upgrade a scratch database with Alembic and compare it with the ORM metadata."""
    admin = create_async_engine("postgresql+asyncpg://prasang:prasang@localhost:5433/postgres", isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text("DROP DATABASE IF EXISTS prasang_migration_check WITH (FORCE)"))
        await conn.execute(text("CREATE DATABASE prasang_migration_check"))
    url = "postgresql+asyncpg://prasang:prasang@localhost:5433/prasang_migration_check"
    env = {**os.environ, "DATABASE_URL": url}
    for args in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(["uv", "run", "alembic", *args], cwd=BACKEND, env=env, check=True, capture_output=True)

    engine = create_async_engine(url)
    async with engine.connect() as conn:
        diff = await conn.run_sync(lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata))
    await engine.dispose()
    async with admin.connect() as conn:
        await conn.execute(text("DROP DATABASE prasang_migration_check WITH (FORCE)"))
    await admin.dispose()
    assert diff == []
