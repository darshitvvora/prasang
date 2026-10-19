"""Plan usage (contract PlanUsage) and IST calendar-month boundaries for lead quotas."""
from datetime import UTC, datetime, timedelta

from app.artists.stats import IST
from app.contract import PlanUsage


def month_bounds_ist(now: datetime) -> tuple[datetime, datetime]:
    """[start, end) of the IST calendar month containing `now`, as UTC datetimes."""
    local = now.astimezone(IST)
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=32)).replace(day=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def previous_month_bounds_ist(now: datetime) -> tuple[datetime, datetime]:
    start, _ = month_bounds_ist(now)
    return month_bounds_ist(start - timedelta(hours=1))


def plan_usage(profile, plan, leads_used: int, now: datetime, subscription=None) -> PlanUsage:
    if profile.tier_source == "trial":
        status = "trial"
    elif profile.tier_source == "paid":
        if subscription is not None and subscription.status == "halted":
            status = "halted"
        elif subscription is not None and subscription.cancel_at_period_end:
            status = "cancelling"
        else:
            status = "active"
    else:
        status = "free"
    limit = plan.lead_limit_monthly
    return PlanUsage(
        tier=profile.subscription_tier, name=plan.name, status=status, lead_limit_monthly=limit,
        leads_used_this_month=leads_used, leads_remaining=None if limit < 0 else max(0, limit - leads_used),
        period_end=subscription.current_period_end if subscription is not None and status != "trial" else None,
        trial_ends_at=profile.trial_ends_at.astimezone(IST).date() if status == "trial" and profile.trial_ends_at else None,
        trial_available=not profile.trial_used and profile.tier_source == "free",
    )
