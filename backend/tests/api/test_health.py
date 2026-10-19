async def test_healthz_reports_process_up(client):
    res = await client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_readyz_checks_dependencies(client):
    res = await client.get("/readyz")
    assert res.status_code == 200
    assert res.json() == {"postgres": "ok", "elasticsearch": "ok", "temporal": "ok"}
