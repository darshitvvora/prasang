"""BookingFollowUpWorkflow: ask the planner whether they booked the artist, so verified reviews can open.

Check-in 1 three days after the inquiry (+ one reminder two days later); check-in 2 the day after the event (or 14 days
after the inquiry without a date) + one reminder. At most 4 messages. Before each send the lead's state is re-read; the
API also sends `settled` when the booking is confirmed or the planner answers yes/no, which ends the workflow at once.
"""
from datetime import date, datetime, time, timedelta, timezone

from temporalio import workflow
from temporalio.common import RetryPolicy

OPTS = {"start_to_close_timeout": timedelta(seconds=30), "retry_policy": RetryPolicy(maximum_attempts=10)}
IST = timezone(timedelta(hours=5, minutes=30))
CHECK_1_AFTER = timedelta(days=3)
REMINDER_AFTER = timedelta(days=2)
NO_DATE_CHECK_2_AFTER = timedelta(days=14)
CHECK_2_LOCAL_TIME = time(10, 0)  # 10 am IST the day after the event


def schedule(inquiry_at: datetime, event_date: date | None) -> list[tuple[datetime, str]]:
    check_1 = inquiry_at + CHECK_1_AFTER
    if event_date is not None:
        check_2 = datetime.combine(event_date + timedelta(days=1), CHECK_2_LOCAL_TIME, tzinfo=IST)
    else:
        check_2 = inquiry_at + NO_DATE_CHECK_2_AFTER
    steps = [(check_1, "booking_check_1"), (check_1 + REMINDER_AFTER, "booking_check_1_reminder")]
    steps = [s for s in steps if s[0] < check_2]  # check-1 messages that would land after check-2 are dropped
    return steps + [(check_2, "booking_check_2"), (check_2 + REMINDER_AFTER, "booking_check_2_reminder")]


@workflow.defn
class BookingFollowUpWorkflow:
    def __init__(self) -> None:
        self.is_settled = False

    @workflow.signal
    def settled(self) -> None:
        self.is_settled = True

    @workflow.run
    async def run(self, lead_id: str, inquiry_at_iso: str, event_date_iso: str | None) -> str:
        event_date = date.fromisoformat(event_date_iso) if event_date_iso else None
        for at, kind in schedule(datetime.fromisoformat(inquiry_at_iso), event_date):
            remaining = at - workflow.now()
            if remaining.total_seconds() > 0:
                try:
                    await workflow.wait_condition(lambda: self.is_settled, timeout=remaining)
                except TimeoutError:
                    pass
            if self.is_settled:
                return "settled"
            state = await workflow.execute_activity("booking_state", lead_id, result_type=str, **OPTS)
            if state == "settled":
                return "settled"
            if state == "deciding" and kind.startswith("booking_check_1"):
                continue
            await workflow.execute_activity("send_booking_check", args=[lead_id, kind], **OPTS)
        return "done"
