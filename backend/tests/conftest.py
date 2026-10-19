"""Test harness: runs against the docker-compose Postgres (`prasang_test` db) and Elasticsearch.

Env is set before the app is imported so Settings picks it up.
"""
import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://prasang:prasang@localhost:5433/prasang_test")
os.environ.setdefault("ES_INDEX_PREFIX", "test_")
os.environ.setdefault("DEV_AUTH_HEADER", "true")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, get_engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def _schema():
    """Create the schema once per test session (drop first so model changes apply)."""
    import app.models  # noqa: F401  - registers every ORM model on Base.metadata

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        if enums := _enum_names():
            await conn.execute(text(f"DROP TYPE IF EXISTS {', '.join(enums)} CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def _enum_names() -> list[str]:
    from sqlalchemy import Enum

    names = set()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, Enum) and col.type.name:
                names.add(col.type.name)
    return sorted(names)


@pytest.fixture(autouse=True)
async def _clean_tables():
    """Each test starts from empty tables."""
    yield
    tables = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if tables:
        async with get_engine().begin() as conn:
            await conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def client():
    from app.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
