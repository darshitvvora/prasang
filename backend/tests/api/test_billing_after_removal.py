"""Final review I3: a deleted or blocked artist must never stay billed silently or get a paid plan back from a late webhook."""
import hashlib
import hmac
import json
from datetime import date, timedelta

from sqlalchemy import select

from app.admin import actions
from app.admin.models import AdminAction
from app.artists.models import ArtistProfile
from app.config import get_settings
from app.db import get_sessionmaker
from app.subscriptions.gateway import FakeGateway
from app.subscriptions.models import Subscription
from tests.helpers import ARTIST, seed_demo

ARJUN = "arjun-malhotra-magic"


class Gateway(FakeGateway):
    def __init__(self, fail_cancel=False):
        self.cancelled: list[tuple[str, bool]] = []
        self.fail_cancel = fail_cancel

    async def cancel_subscription(self, gateway_subscription_id, at_cycle_end):
        if self.fail_cancel:
            raise RuntimeError("razorpay down")
        self.cancelled.append((gateway_subscription_id, at_cycle_end))


def _install(monkeypatch, g):
    monkeypatch.setattr("app.subscriptions.service.get_gateway", lambda: g)
    monkeypatch.setattr("app.subscriptions.router.get_gateway", lambda: g)
    monkeypatch.setattr("app.admin.actions.revoke_sessions", _noop)
    monkeypatch.setattr(get_settings(), "razorpay_webhook_secret", "whsec")


async def _noop(user_id):
    return None


async def _add_sub(status="active", gid="sub_x"):
    async with get_sessionmaker()() as s:
        artist = (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()
        s.add(Subscription(artist_id=artist.id, tier="pro", billing_cycle="monthly", status=status, gateway_subscription_id=gid,
                           current_period_end=date.today() + timedelta(days=10)))
        await s.commit()


async def _charged(client, gid):
    entity = {"id": gid, "status": "active", "current_end": 1893456000}
    body = json.dumps({"event": "subscription.charged", "payload": {"subscription": {"entity": entity}}}).encode()
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    return await client.post("/api/v1/subscriptions/webhook", content=body, headers={
        "X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": f"evt-{gid}", "Content-Type": "application/json"})


async def _arjun():
    async with get_sessionmaker()() as s:
        return (await s.execute(select(ArtistProfile).where(ArtistProfile.slug == ARJUN))).scalar_one()


async def test_deletion_with_gateway_failure_is_flagged_not_hidden(client, monkeypatch):
    _install(monkeypatch, Gateway(fail_cancel=True))
    await seed_demo()
    await _add_sub()
    assert (await client.delete("/api/v1/me", headers=ARTIST)).status_code == 204
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(Subscription))).scalar_one().status == "active"  # still billing at Razorpay
        flagged = (await s.execute(select(AdminAction).where(AdminAction.action == "manual_cancel_needed"))).scalars().all()
        assert [f.target_id for f in flagged] == ["sub_x"]
        reports = await actions.open_reports(s)
    assert [r["gateway_subscription_id"] for r in reports["billing"]] == ["sub_x"]


async def test_late_charge_after_deletion_cancels_instead_of_restoring(client, monkeypatch):
    g = Gateway()
    _install(monkeypatch, g)
    await seed_demo()
    await _add_sub(status="created", gid="sub_late")
    await client.delete("/api/v1/me", headers=ARTIST)
    g.cancelled.clear()
    assert (await _charged(client, "sub_late")).status_code == 200
    artist = await _arjun()
    assert (artist.subscription_tier, artist.tier_source) == ("free", "free")
    assert g.cancelled == [("sub_late", False)]


async def test_late_charge_after_block_cancels_instead_of_restoring(client, monkeypatch):
    g = Gateway()
    _install(monkeypatch, g)
    await seed_demo()
    await _add_sub(status="created", gid="sub_open_checkout")
    async with get_sessionmaker()() as s:
        await actions.block_user(s, "dev-artist-arjun", actor="test", reason="fraud")
    assert ("sub_open_checkout", False) in g.cancelled  # open checkouts are cancelled too
    g.cancelled.clear()
    before = await _arjun()
    await _charged(client, "sub_open_checkout")
    after = await _arjun()
    assert (after.subscription_tier, after.tier_source) == (before.subscription_tier, before.tier_source)  # no plan restored
    async with get_sessionmaker()() as s:
        assert (await s.execute(select(Subscription))).scalar_one().status == "cancelled"
    assert g.cancelled == [("sub_open_checkout", False)]
