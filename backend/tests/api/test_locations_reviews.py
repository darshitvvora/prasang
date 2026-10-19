from tests.helpers import seed_demo


async def test_locations(client):
    await seed_demo()
    res = await client.get("/api/v1/locations")
    cities = {c["name"]: c["areas"] for c in res.json()["cities"]}
    assert cities["Mumbai"][:2] == ["Bandra West", "Andheri West"]
    assert cities["Jaipur"] == []
    assert list(cities)[0] == "Mumbai"


async def test_reviews_page(client):
    await seed_demo()
    res = await client.get("/api/v1/artists/arjun-malhotra-magic/reviews?page=1&size=2")
    body = res.json()
    assert (body["total"], body["page"], body["size"], len(body["items"])) == (3, 1, 2, 2)
    assert body["items"][0]["eventMonth"] == "2026-08"
    assert (await client.get("/api/v1/artists/nobody/reviews")).status_code == 404
