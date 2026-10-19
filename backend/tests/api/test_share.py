from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from tests.helpers import seed_demo

INDEX = '<html><head><!--og:start--><title>Prasang</title><meta property="og:title" content="Prasang" /><!--og:end--></head><body><div id="root"></div></body></html>'


def _client(tmp_path=None) -> AsyncClient:
    from app.main import create_app

    kw = {}
    if tmp_path is not None:
        index = tmp_path / "index.html"
        index.write_text(INDEX)
        kw["web_index_path"] = str(index)
    settings = Settings(env="test", dev_auth_header=True, public_web_url="https://prasang.in", **kw)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_profile_page_has_artist_tags(tmp_path):
    await seed_demo()
    async with _client(tmp_path) as c:
        res = await c.get("/profile/arjun-malhotra-magic")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert 'property="og:title" content="Arjun Malhotra · Magician · Mumbai"' in res.text
    assert '<div id="root"></div>' in res.text


async def test_profile_page_unknown_slug_serves_generic_index(tmp_path):
    await seed_demo()
    async with _client(tmp_path) as c:
        res = await c.get("/profile/nobody-here")
    assert res.status_code == 200
    assert res.text == INDEX


async def test_share_head_returns_fragment():
    await seed_demo()
    async with _client() as c:
        res = await c.get("/api/v1/artists/arjun-malhotra-magic/share-head")
    assert res.status_code == 200
    assert res.text.startswith("<title>Arjun Malhotra · Magician · Mumbai</title>")


async def test_share_head_unknown_slug_404():
    async with _client() as c:
        res = await c.get("/api/v1/artists/nobody-here/share-head")
    assert res.status_code == 404


async def test_profile_page_without_index_path_503():
    async with _client() as c:
        res = await c.get("/profile/arjun-malhotra-magic")
    assert res.status_code == 503
