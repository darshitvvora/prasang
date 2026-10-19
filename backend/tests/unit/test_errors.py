import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.errors import AppError, install_error_handlers, not_found
from app.schemas import RequestModel


class Body(RequestModel):
    full_name: str
    per_event_rate_max: int | None = None


def make_app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/missing")
    async def missing():
        raise not_found("artist_not_found", "No artist found for this link")

    @app.post("/body")
    async def body(b: Body):
        return {"ok": b.full_name}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internals")

    return app


@pytest.fixture
async def app_client():
    async with AsyncClient(transport=ASGITransport(app=make_app(), raise_app_exceptions=False), base_url="http://t") as c:
        yield c


async def test_app_error_uses_contract_body(app_client):
    res = await app_client.get("/missing")
    assert res.status_code == 404
    assert res.json() == {"error": {"code": "artist_not_found", "message": "No artist found for this link", "details": {}}}


async def test_validation_errors_map_camelcase_fields(app_client):
    res = await app_client.post("/body", json={"fullName": 5, "perEventRateMax": "lots"})
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["code"] == "validation_error"
    assert set(body["details"]["fields"]) == {"fullName", "perEventRateMax"}


async def test_unknown_fields_are_rejected(app_client):
    res = await app_client.post("/body", json={"fullName": "A", "hacker": True})
    assert res.status_code == 422
    assert "hacker" in res.json()["error"]["details"]["fields"]


async def test_unhandled_errors_hide_internals(app_client):
    res = await app_client.get("/boom")
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "internal_error"
    assert "secret" not in res.text


def test_production_refuses_dev_auth_header():
    with pytest.raises(ValueError, match="DEV_AUTH_HEADER"):
        Settings(env="production", dev_auth_header=True, database_url="postgresql+asyncpg://x/y").validate_for_env()


def test_app_error_carries_details():
    err = AppError(409, "media_quota_exceeded", "Limit reached", {"limit": 5, "used": 5})
    assert (err.status, err.code, err.details) == (409, "media_quota_exceeded", {"limit": 5, "used": 5})


def test_public_https_domains_require_production_env():
    """Review fix Important 7: a real deployment that forgets ENV=production must not start with insecure cookies."""
    s = Settings(env="local", api_domain="https://api.prasang.in", website_domain="https://prasang.in", database_url="postgresql+asyncpg://x/y")
    with pytest.raises(ValueError, match="ENV=production"):
        s.validate_for_env()
    Settings(env="local", api_domain="http://localhost:5173", database_url="postgresql+asyncpg://x/y").validate_for_env()
    Settings(env="production", dev_auth_header=False, api_domain="https://api.prasang.in", website_domain="https://prasang.in",
             database_url="postgresql+asyncpg://x/y").validate_for_env()
