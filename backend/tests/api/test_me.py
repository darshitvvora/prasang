from tests.helpers import NEW, PLANNER, seed_demo


async def test_me_requires_auth(client):
    res = await client.get("/api/v1/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthenticated"


async def test_signed_in_user_without_profile_gets_profile_required(client):
    res = await client.get("/api/v1/me", headers=NEW)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "profile_required"


async def test_create_profile_then_conflict(client):
    res = await client.post("/api/v1/me", headers=NEW, json={"role": "artist", "fullName": "Tanvi Rao"})
    assert res.status_code == 201
    body = res.json()
    assert (body["role"], body["fullName"], body["artistSlug"], body["email"]) == ("artist", "Tanvi Rao", None, "new.user@gmail.com")
    assert body["createdAt"].endswith("Z")

    again = await client.post("/api/v1/me", headers=NEW, json={"role": "planner", "fullName": "Tanvi"})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "profile_exists"


async def test_admin_role_cannot_be_self_assigned(client):
    res = await client.post("/api/v1/me", headers=NEW, json={"role": "admin", "fullName": "Mallory"})
    assert res.status_code == 422
    assert "role" in res.json()["error"]["details"]["fields"]


async def test_invalid_phone_is_rejected(client):
    res = await client.post("/api/v1/me", headers=NEW, json={"role": "planner", "fullName": "A", "phone": "12345"})
    assert res.status_code == 422
    assert "phone" in res.json()["error"]["details"]["fields"]


async def test_planner_me_and_update(client):
    await seed_demo()
    res = await client.get("/api/v1/me", headers=PLANNER)
    assert res.status_code == 200
    assert res.json()["fullName"] == "Neha Kulkarni"

    res = await client.patch("/api/v1/me", headers=PLANNER, json={"fullName": "Neha K."})
    assert res.status_code == 200
    assert res.json()["fullName"] == "Neha K."


async def test_artist_me_includes_slug(client):
    await seed_demo()
    res = await client.get("/api/v1/me", headers={"Authorization": "Bearer mock-artist"})
    assert res.json()["artistSlug"] == "arjun-malhotra-magic"


async def test_auth_providers_reflect_configuration(client):
    res = await client.get("/api/v1/auth/providers")
    assert res.status_code == 200
    assert res.json() == {"google": False, "phoneOtp": True}
