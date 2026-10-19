"""Booking confirmation: either the artist ("converted") or the planner ("Yes, I booked") confirms; neither can block the other."""
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.artists.models import ArtistProfile
from app.auth.models import User
from app.db import get_sessionmaker
from app.leads.models import Lead
from tests.helpers import ARTIST, PLANNER, seed_demo

ARJUN = "arjun-malhotra-magic"


class RecordingStarter:
    def __init__(self):
        self.settled: list[str] = []

    async def signal_booking_settled(self, lead_id: str) -> None:
        self.settled.append(lead_id)

    def __getattr__(self, name):  # every other starter call is a no-op here
        async def _noop(*args, **kwargs):
            return None
        return _noop


@pytest.fixture
def starter(monkeypatch):
    s = RecordingStarter()
    monkeypatch.setattr("app.leads.booking.get_starter", lambda: s)
    return s


async def _lead(status="new", event_date: date | None = None, planner_id="dev-planner-neha", locked=False) -> str:
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        lead = Lead(artist_id=artist.id, planner_id=planner_id, planner_name="Neha Kulkarni", planner_phone="9920012345",
                    event_type="wedding", event_date=event_date, budget_range="15k_25k", budget_min=15000, budget_max=25000,
                    source="profile", status=status, is_locked=locked, created_at=datetime.now(UTC))
        s.add(lead)
        await s.commit()
        return str(lead.id)


async def _get(lead_id: str) -> Lead:
    async with get_sessionmaker()() as s:
        return await s.get(Lead, lead_id)


async def _answer(client, lead_id, answer, headers=PLANNER):
    return await client.patch(f"/api/v1/leads/{lead_id}/planner-answer", headers=headers, json={"answer": answer})


async def test_planner_booked_confirms_and_converts(client, starter):
    await seed_demo()
    lid = await _lead("contacted")
    res = await _answer(client, lid, "booked")
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["bookingConfirmed"], body["plannerAnswer"], body["status"]) == (True, "booked", "confirmed")
    lead = await _get(lid)
    assert (lead.status, lead.booking_confirmed_by) == ("converted", "planner")
    assert starter.settled == [lid]


async def test_planner_booked_on_expired_lead_converts(client, starter):
    await seed_demo()
    lid = await _lead("expired", event_date=date.today() - timedelta(days=1))
    await _answer(client, lid, "booked")
    assert (await _get(lid)).status == "converted"


async def test_planner_booked_on_declined_lead_keeps_status_but_confirms(client, starter):
    await seed_demo()
    lid = await _lead("declined")
    body = (await _answer(client, lid, "booked")).json()
    lead = await _get(lid)
    assert lead.status == "declined" and lead.booking_confirmed_at is not None
    assert body["bookingConfirmed"] is True


async def test_planner_not_booked_keeps_artist_status(client, starter):
    await seed_demo()
    lid = await _lead("contacted")
    body = (await _answer(client, lid, "not_booked")).json()
    lead = await _get(lid)
    assert (lead.status, lead.planner_answer, lead.booking_confirmed_at) == ("contacted", "not_booked", None)
    assert body["bookingConfirmed"] is False
    assert starter.settled == [lid]


async def test_planner_deciding_does_not_settle(client, starter):
    await seed_demo()
    lid = await _lead("new")
    await _answer(client, lid, "deciding")
    assert (await _get(lid)).planner_answer == "deciding"
    assert starter.settled == []


async def test_artist_converted_confirms_by_artist(client, starter):
    await seed_demo()
    lid = await _lead("contacted")
    res = await client.patch(f"/api/v1/leads/{lid}", headers=ARTIST, json={"status": "converted"})
    assert res.status_code == 200
    lead = await _get(lid)
    assert lead.booking_confirmed_by == "artist" and lead.booking_confirmed_at is not None
    assert starter.settled == [lid]


async def test_other_planner_gets_404(client, starter):
    await seed_demo()
    async with get_sessionmaker()() as s:
        s.add(User(id="other-planner", full_name="Other", role="planner"))
        await s.commit()
    lid = await _lead("new", planner_id="other-planner")
    res = await _answer(client, lid, "booked")
    assert res.status_code == 404 and res.json()["error"]["code"] == "lead_not_found"
    assert (await _answer(client, "not-a-uuid", "booked")).status_code == 404


async def test_can_review_only_after_event_date(client, starter):
    await seed_demo()
    future = await _lead("contacted", event_date=date.today() + timedelta(days=10))
    past = await _lead("contacted", event_date=date.today() - timedelta(days=2))
    undated = await _lead("contacted")
    for lid in (future, past, undated):
        await _answer(client, lid, "booked")
    items = {i["id"]: i for i in (await client.get("/api/v1/leads/planner", headers=PLANNER)).json()["items"]}
    assert items[future]["canReview"] is False
    assert items[past]["canReview"] is True
    assert items[undated]["canReview"] is True
    assert items[past]["reviewId"] is None


async def test_locked_lead_can_be_confirmed(client, starter):
    await seed_demo()
    lid = await _lead("new", locked=True)
    body = (await _answer(client, lid, "booked")).json()
    assert body["bookingConfirmed"] is True


async def test_checkins_stop_when_artist_is_gone(client, starter):
    """Final review M1 (regraded): no "Did you book …?" texts about suspended or deleted artists."""
    from app.leads.booking import booking_state

    await seed_demo()
    lid = await _lead("contacted")
    async with get_sessionmaker()() as s:
        assert await booking_state(s, lid) == "open"
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        artist.suspended_at = datetime.now(UTC)
        await s.commit()
        assert await booking_state(s, lid) == "settled"
        artist.suspended_at, artist.is_published = None, False  # deleted artists are unpublished
        await s.commit()
        assert await booking_state(s, lid) == "settled"
