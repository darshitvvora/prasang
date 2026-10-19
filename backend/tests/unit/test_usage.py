from datetime import UTC, datetime
from types import SimpleNamespace

from app.leads.usage import month_bounds_ist, plan_usage


def test_ist_month_boundary():
    # 2026-10-31 19:00 UTC is already 1 Nov 00:30 in India
    start, end = month_bounds_ist(datetime(2026, 10, 31, 19, 0, tzinfo=UTC))
    assert start == datetime(2026, 10, 31, 18, 30, tzinfo=UTC)
    assert end == datetime(2026, 11, 30, 18, 30, tzinfo=UTC)


def _profile(**kw):
    return SimpleNamespace(**({"tier_source": "free", "subscription_tier": "free", "trial_used": False, "trial_ends_at": None} | kw))


def test_free_plan_usage():
    u = plan_usage(_profile(), SimpleNamespace(name="Free", lead_limit_monthly=3), 5, datetime.now(UTC))
    assert (u.status, u.leads_remaining, u.trial_available) == ("free", 0, True)


def test_unlimited_plan_has_no_remaining_count():
    u = plan_usage(_profile(tier_source="paid", subscription_tier="pro"), SimpleNamespace(name="Pro", lead_limit_monthly=-1), 40, datetime.now(UTC))
    assert (u.status, u.leads_remaining, u.trial_available) == ("active", None, False)
