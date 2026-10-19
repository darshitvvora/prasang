"""Booking check-ins in Temporal's time-skipping server, with mocked activities."""
import uuid
from datetime import datetime, timedelta

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.workflows.booking_followup import BookingFollowUpWorkflow

SENT: list[tuple[str, datetime]] = []
STATE = {"value": "open"}


@activity.defn(name="booking_state")
async def booking_state(lead_id: str) -> str:
    return STATE["value"]


@activity.defn(name="send_booking_check")
async def send_booking_check(lead_id: str, kind: str) -> None:
    SENT.append((kind, activity.info().scheduled_time))  # workflow (time-skipped) clock


async def _run(env, inquiry_at: datetime, event_date: str | None, during=None):
    queue = str(uuid.uuid4())
    async with Worker(env.client, task_queue=queue, workflows=[BookingFollowUpWorkflow],
                      activities=[booking_state, send_booking_check]):
        handle = await env.client.start_workflow(BookingFollowUpWorkflow.run, args=["lead-1", inquiry_at.isoformat(), event_date],
                                                 id=f"booking-{uuid.uuid4()}", task_queue=queue)
        if during:
            await during(env, handle)
        return await handle.result()


def _reset(state="open"):
    SENT.clear()
    STATE["value"] = state


def _days(delta: timedelta) -> int:
    return round(delta.total_seconds() / 86400)  # scheduled times jitter by milliseconds


def _kinds() -> list[str]:
    return [k for k, _ in SENT]


async def test_no_answer_sends_four_messages_in_order():
    _reset()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        start = await env.get_current_time()
        event = (start + timedelta(days=20)).date()
        await _run(env, start, event.isoformat())
    assert _kinds() == ["booking_check_1", "booking_check_1_reminder", "booking_check_2", "booking_check_2_reminder"]
    days = [_days(t - start) for _, t in SENT]
    assert days[0] == 3 and days[1] == 5
    assert SENT[2][1].date() >= event + timedelta(days=1) and _days(SENT[3][1] - SENT[2][1]) == 2


async def test_confirmed_after_check1_sends_nothing_more():
    _reset()

    async def confirm_after_first(env, handle):
        await env.sleep(timedelta(days=4))  # check-1 went out on day 3
        STATE["value"] = "settled"
        await handle.signal(BookingFollowUpWorkflow.settled)

    async with await WorkflowEnvironment.start_time_skipping() as env:
        start = await env.get_current_time()
        result = await _run(env, start, (start + timedelta(days=20)).date().isoformat(), confirm_after_first)
    assert _kinds() == ["booking_check_1"]
    assert result == "settled"


async def test_settled_state_without_signal_also_stops():
    _reset()

    async def settle_quietly(env, handle):
        await env.sleep(timedelta(days=4))
        STATE["value"] = "settled"  # e.g. the signal was lost while Temporal was down

    async with await WorkflowEnvironment.start_time_skipping() as env:
        start = await env.get_current_time()
        await _run(env, start, (start + timedelta(days=20)).date().isoformat(), settle_quietly)
    assert _kinds() == ["booking_check_1"]


async def test_deciding_skips_to_check2():
    _reset("deciding")
    async with await WorkflowEnvironment.start_time_skipping() as env:
        start = await env.get_current_time()
        await _run(env, start, (start + timedelta(days=20)).date().isoformat())
    assert _kinds() == ["booking_check_2", "booking_check_2_reminder"]


async def test_no_event_date_uses_day_14():
    _reset()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        start = await env.get_current_time()
        await _run(env, start, None)
    assert _kinds() == ["booking_check_1", "booking_check_1_reminder", "booking_check_2", "booking_check_2_reminder"]
    assert _days(SENT[2][1] - start) == 14


async def test_event_soon_skips_overlapping_reminder():
    _reset()
    async with await WorkflowEnvironment.start_time_skipping() as env:
        start = await env.get_current_time()
        await _run(env, start, (start + timedelta(days=3)).date().isoformat())  # check-2 on day 4, before the day-5 reminder
    assert _kinds() == ["booking_check_1", "booking_check_2", "booking_check_2_reminder"]
