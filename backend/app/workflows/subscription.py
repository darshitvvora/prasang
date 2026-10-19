"""Durable timers for paid plans and trials. State changes come in as signals from the API (verify/webhooks)."""
from datetime import datetime, timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

ACTIVATION_WINDOW = timedelta(hours=24)
GRACE = timedelta(days=3)
OPTS = {"start_to_close_timeout": timedelta(seconds=30), "retry_policy": RetryPolicy(maximum_attempts=10)}


@workflow.defn
class SubscriptionWorkflow:
    """created → (activated within 24h, else expire) → active until period end + 3 days without a charge (lapse) or ended."""

    def __init__(self) -> None:
        self.period_end: datetime | None = None
        self.ended: str | None = None
        self.version = 0

    @workflow.signal
    def activated(self, period_end_iso: str) -> None:
        self.period_end = datetime.fromisoformat(period_end_iso)
        self.version += 1

    @workflow.signal
    def charged(self, period_end_iso: str) -> None:
        self.period_end = datetime.fromisoformat(period_end_iso)
        self.version += 1

    @workflow.signal
    def ended(self, status: str) -> None:
        self.ended = status

    @workflow.run
    async def run(self, subscription_id: str, period_end_iso: str | None = None) -> str:
        if period_end_iso:  # continued-as-new
            self.period_end = datetime.fromisoformat(period_end_iso)
        else:
            try:
                await workflow.wait_condition(lambda: self.period_end is not None or self.ended is not None, timeout=ACTIVATION_WINDOW)
            except TimeoutError:
                await workflow.execute_activity("expire_unpaid_subscription", subscription_id, **OPTS)
                return "expired"

        while self.ended is None:
            seen = self.version
            remaining = self.period_end + GRACE - workflow.now()
            if remaining.total_seconds() <= 0:
                await workflow.execute_activity("lapse_subscription", subscription_id, **OPTS)
                return "lapsed"
            try:
                await workflow.wait_condition(lambda seen=seen: self.version != seen or self.ended is not None, timeout=remaining)
            except TimeoutError:
                await workflow.execute_activity("lapse_subscription", subscription_id, **OPTS)
                return "lapsed"
            if self.ended is None and workflow.info().is_continue_as_new_suggested():
                workflow.continue_as_new(args=[subscription_id, self.period_end.isoformat()])
        return self.ended


@workflow.defn
class TrialWorkflow:
    @workflow.run
    async def run(self, artist_id: str, ends_at_iso: str) -> None:
        remaining = datetime.fromisoformat(ends_at_iso) - workflow.now()
        if remaining.total_seconds() > 0:
            await workflow.sleep(remaining)
        await workflow.execute_activity("end_trial", artist_id, **OPTS)
