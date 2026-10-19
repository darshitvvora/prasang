"""current_user / require_role behaviour (Review Focus 5: no profile row → 404 profile_required, never 500)."""
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.deps import current_user, require_role
from app.config import get_settings
from app.errors import install_error_handlers
from tests.helpers import ARTIST, NEW, PLANNER, seed_demo


def make_app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/artist-only")
    async def artist_only(user=Depends(require_role("artist"))):
        return {"id": user.id}

    @app.get("/any-user")
    async def any_user(user=Depends(current_user)):
        return {"id": user.id}

    return app


@pytest.fixture
async def c():
    async with AsyncClient(transport=ASGITransport(app=make_app()), base_url="http://t") as client:
        yield client


async def test_identity_without_profile_row_is_profile_required(c):
    for path in ("/artist-only", "/any-user"):
        res = await c.get(path, headers=NEW)
        assert res.status_code == 404, path
        assert res.json()["error"]["code"] == "profile_required"


async def test_wrong_role_is_forbidden(c):
    await seed_demo()
    res = await c.get("/artist-only", headers=PLANNER)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "forbidden"


async def test_right_role_passes(c):
    await seed_demo()
    res = await c.get("/artist-only", headers=ARTIST)
    assert res.json() == {"id": "dev-artist-arjun"}


async def test_unknown_mock_token_is_unauthenticated(c):
    res = await c.get("/any-user", headers={"Authorization": "Bearer mock-hacker"})
    assert res.status_code == 401


async def test_dev_header_ignored_when_disabled(c, monkeypatch):
    monkeypatch.setattr(get_settings(), "dev_auth_header", False)
    res = await c.get("/any-user", headers=ARTIST)
    assert res.status_code == 401
