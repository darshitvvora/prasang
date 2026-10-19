"""Review Focus 3: a Temporal outage must not lose the lead or hide the artist's contact from the planner."""
from datetime import date, timedelta

from app.workflows.starter import NoopStarter, set_starter
from tests.api.test_leads import artist_id, lead_body
from tests.helpers import PLANNER, seed_demo


class Recording:
    def __init__(self):
        self.started: list[str] = []

    async def start_lead_notification(self, lead_id: str) -> None:
        self.started.append(lead_id)


class Down:
    async def start_lead_notification(self, lead_id: str) -> None:
        raise ConnectionError("temporal unreachable")


async def test_lead_starts_notification_workflow(client):
    await seed_demo()
    rec = Recording()
    set_starter(rec)
    try:
        aid = await artist_id(client, "dj-krish")
        res = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=(date.today() + timedelta(days=45)).isoformat()))
        assert res.status_code == 201 and rec.started == [res.json()["leadId"]]
        again = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid, eventDate=(date.today() + timedelta(days=45)).isoformat()))
        assert again.status_code == 200 and len(rec.started) == 1  # duplicates don't re-notify
    finally:
        set_starter(NoopStarter())


async def test_temporal_outage_still_returns_contact(client):
    await seed_demo()
    set_starter(Down())
    try:
        aid = await artist_id(client, "dj-krish")
        res = await client.post("/api/v1/leads", headers=PLANNER, json=lead_body(aid))
        assert res.status_code == 201 and res.json()["artist"]["contactPhone"] == "9820011002"
    finally:
        set_starter(NoopStarter())
