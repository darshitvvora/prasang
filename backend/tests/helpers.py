"""Shared test helpers. Dev tokens act as demo users when DEV_AUTH_HEADER=true (set in conftest)."""
ARTIST = {"Authorization": "Bearer mock-artist"}
PLANNER = {"Authorization": "Bearer mock-planner"}
NEW = {"Authorization": "Bearer mock-new"}


async def seed_demo():
    from app.db import get_sessionmaker
    from app.seed import seed

    async with get_sessionmaker()() as session:
        await seed(session, demo=True)


async def seed_base():
    from app.db import get_sessionmaker
    from app.seed import seed

    async with get_sessionmaker()() as session:
        await seed(session, demo=False)
