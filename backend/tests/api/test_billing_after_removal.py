"""A deleted or blocked artist must never be left with a payable link or get a plan back from a late payment."""
import pytest
from sqlalchemy import select

from app.admin import actions
from app.admin.models import AdminAction
from app.db import get_sessionmaker
from tests.api.phonepe import Gateway, arjun, install, order_of, subs, subscribe, webhook
from tests.helpers import ARTIST, seed_demo


async def _noop(user_id):
    return None


@pytest.fixture
def gateway(monkeypatch):
    g = Gateway()
    install(monkeypatch, g)
    monkeypatch.setattr("app.admin.actions.revoke_sessions", _noop)
    return g


async def _flags(action: str) -> list[str]:
    async with get_sessionmaker()() as s:
        return list((await s.execute(select(AdminAction.target_id).where(AdminAction.action == action))).scalars())


async def test_deletion_cancels_open_link_and_flags_when_phonepe_is_down(client, gateway):
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    gateway.fail_cancel = True
    assert (await client.delete("/api/v1/me", headers=ARTIST)).status_code == 204
    assert [s.status for s in await subs()] == ["created"]  # still payable at PhonePe: shown, not hidden
    assert await _flags("manual_cancel_needed") == [order]
    async with get_sessionmaker()() as s:
        reports = await actions.open_reports(s)
    assert [(r["action"], r["gateway_subscription_id"]) for r in reports["billing"]] == [("manual_cancel_needed", order)]


async def test_late_payment_after_deletion_is_flagged_for_refund(client, gateway):
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    await client.delete("/api/v1/me", headers=ARTIST)
    assert gateway.cancelled == [order]
    assert (await webhook(client, order)).status_code == 200
    artist = await arjun()
    assert (artist.subscription_tier, artist.tier_source) == ("free", "free")
    assert await _flags("refund_needed") == [order]


async def test_block_cancels_open_links_and_late_payment_restores_nothing(client, gateway):
    await seed_demo()
    order = await order_of((await subscribe(client))["subscriptionId"])
    async with get_sessionmaker()() as s:
        await actions.block_user(s, "dev-artist-arjun", actor="test", reason="fraud")
    assert gateway.cancelled == [order]
    before = await arjun()
    await webhook(client, order)
    after = await arjun()
    assert (after.subscription_tier, after.tier_source) == (before.subscription_tier, before.tier_source)
    assert [s.status for s in await subs()] == ["cancelled"] and await _flags("refund_needed") == [order]
