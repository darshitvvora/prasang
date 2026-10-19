"""Verified reviews: only for confirmed bookings after the event, one per inquiry, editable for 7 days; artists reply/report."""
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.auth.models import User
from app.db import get_sessionmaker
from app.leads.models import Lead
from app.reviews.models import Review, ReviewReport
from app.search.es import alias, get_es
from app.search.projector import EsIndexer, project_batch, reindex_all
from tests.helpers import ARTIST, PLANNER, seed_demo

ARJUN = "arjun-malhotra-magic"
TEXT = "Arjun kept 40 kids spellbound for an hour. Brilliant!"


async def _lead(confirmed=True, event_date: date | None = None, planner_id="dev-planner-neha", slug=ARJUN) -> str:
    event_date = event_date if event_date is not None else date.today() - timedelta(days=3)
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == slug))).scalar_one()
        lead = Lead(artist_id=artist.id, planner_id=planner_id, planner_name="Neha Kulkarni", planner_phone="9920012345",
                    event_type="birthday", event_date=event_date, budget_range="15k_25k", budget_min=15000, budget_max=25000,
                    source="profile", status="converted" if confirmed else "contacted", is_locked=False,
                    created_at=datetime.now(UTC) - timedelta(days=10),
                    booking_confirmed_at=datetime.now(UTC) if confirmed else None, booking_confirmed_by="planner" if confirmed else None)
        s.add(lead)
        await s.commit()
        return str(lead.id)


async def _review(client, lead_id, headers=PLANNER, rating=5, text=TEXT):
    return await client.post("/api/v1/reviews", headers=headers, json={"leadId": lead_id, "rating": rating, "text": text})


async def test_planner_can_review_confirmed_past_event(client):
    await seed_demo()
    res = await _review(client, await _lead())
    assert res.status_code == 201, res.text
    body = res.json()
    assert (body["rating"], body["verified"], body["reviewerName"], body["eventType"], body["artistReply"]) == (
        5, True, "Neha K.", "birthday", None)
    listed = (await client.get(f"/api/v1/artists/{ARJUN}/reviews")).json()
    assert listed["items"][0]["id"] == body["id"] and listed["items"][0]["verified"] is True


async def test_cannot_review_before_event_date(client):
    await seed_demo()
    res = await _review(client, await _lead(event_date=date.today() + timedelta(days=5)))
    assert res.status_code == 403 and res.json()["error"]["code"] == "review_not_allowed"


async def test_cannot_review_unconfirmed(client):
    await seed_demo()
    res = await _review(client, await _lead(confirmed=False))
    assert res.status_code == 403 and res.json()["error"]["code"] == "review_not_allowed"


async def test_one_review_per_lead(client):
    await seed_demo()
    lid = await _lead()
    assert (await _review(client, lid)).status_code == 201
    res = await _review(client, lid)
    assert res.status_code == 409 and res.json()["error"]["code"] == "review_exists"


async def test_other_planner_cannot_review_404(client):
    await seed_demo()
    async with get_sessionmaker()() as s:
        s.add(User(id="other-planner", full_name="Other Person", role="planner"))
        await s.commit()
    res = await _review(client, await _lead(planner_id="other-planner"))
    assert res.status_code == 404 and res.json()["error"]["code"] == "lead_not_found"


async def test_text_too_short_422(client):
    await seed_demo()
    res = await _review(client, await _lead(), text="Nice")
    assert res.status_code == 422 and "text" in res.json()["error"]["details"]["fields"]


async def test_edit_within_7_days_then_locked(client):
    await seed_demo()
    rid = (await _review(client, await _lead())).json()["id"]
    res = await client.patch(f"/api/v1/reviews/{rid}", headers=PLANNER, json={"rating": 4})
    assert res.status_code == 200 and res.json()["rating"] == 4
    async with get_sessionmaker()() as s:
        review = await s.get(Review, rid)
        review.created_at = datetime.now(UTC) - timedelta(days=8)
        await s.commit()
    res = await client.patch(f"/api/v1/reviews/{rid}", headers=PLANNER, json={"rating": 1})
    assert res.status_code == 409 and res.json()["error"]["code"] == "review_locked"


async def test_artist_reply_shows_publicly(client):
    await seed_demo()
    rid = (await _review(client, await _lead())).json()["id"]
    res = await client.put(f"/api/v1/reviews/{rid}/reply", headers=ARTIST, json={"text": "Thank you, Neha! It was a joy."})
    assert res.status_code == 200 and res.json()["artistReply"] == "Thank you, Neha! It was a joy."
    listed = (await client.get(f"/api/v1/artists/{ARJUN}/reviews")).json()["items"]
    assert next(r for r in listed if r["id"] == rid)["artistReply"] == "Thank you, Neha! It was a joy."


async def test_other_artist_reply_404(client):
    await seed_demo()
    rid = (await _review(client, await _lead(slug="dj-krish"))).json()["id"]
    res = await client.put(f"/api/v1/reviews/{rid}/reply", headers=ARTIST, json={"text": "Not my review"})
    assert res.status_code == 404
    res = await client.post(f"/api/v1/reviews/{rid}/report", headers=ARTIST, json={"reason": "Trying to report someone else's review"})
    assert res.status_code == 404


async def test_report_listed_by_admin_reports(client):
    await seed_demo()
    rid = (await _review(client, await _lead())).json()["id"]
    res = await client.post(f"/api/v1/reviews/{rid}/report", headers=ARTIST, json={"reason": "This person never booked me."})
    assert res.status_code == 204
    assert (await client.post(f"/api/v1/reviews/{rid}/report", headers=ARTIST, json={"reason": "Again, never booked."})).status_code == 204
    from app.admin.actions import open_reports

    async with get_sessionmaker()() as s:
        reports = await open_reports(s)
        assert len((await s.execute(select(ReviewReport))).scalars().all()) == 1
    assert [r["review_id"] for r in reports["reviews"]] == [rid]


async def test_rating_aggregates_update_and_reach_search(client):
    await seed_demo()
    es = get_es()
    await reindex_all(get_sessionmaker(), es)
    await _review(client, await _lead(), rating=1)
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        rows = (await s.execute(select(Review.rating).where(Review.artist_id == artist.id))).scalars().all()
        assert artist.total_reviews == len(rows)
        assert artist.average_rating == pytest.approx(round(sum(rows) / len(rows), 2))
    await project_batch(get_sessionmaker(), EsIndexer(es))
    await es.indices.refresh(index=alias())
    doc = (await es.search(index=alias(), body={"query": {"term": {"slug": ARJUN}}}))["hits"]["hits"][0]["_source"]
    assert doc["total_reviews"] == len(rows)
    await es.close()


async def test_hidden_review_not_listed(client):
    await seed_demo()
    rid = (await _review(client, await _lead())).json()["id"]
    async with get_sessionmaker()() as s:
        (await s.get(Review, rid)).hidden_at = datetime.now(UTC)
        await s.commit()
    ids = [r["id"] for r in (await client.get(f"/api/v1/artists/{ARJUN}/reviews")).json()["items"]]
    assert rid not in ids


async def test_inquiry_shows_review_id_after_review(client):
    await seed_demo()
    lid = await _lead()
    rid = (await _review(client, lid)).json()["id"]
    item = next(i for i in (await client.get("/api/v1/leads/planner", headers=PLANNER)).json()["items"] if i["id"] == lid)
    assert (item["reviewId"], item["canReview"]) == (rid, False)


async def test_artist_sees_own_reviews(client):
    await seed_demo()
    rid = (await _review(client, await _lead())).json()["id"]
    body = (await client.get("/api/v1/reviews/mine", headers=ARTIST)).json()
    assert body["items"][0]["id"] == rid
    assert (await client.get("/api/v1/reviews/mine", headers=PLANNER)).status_code == 403
