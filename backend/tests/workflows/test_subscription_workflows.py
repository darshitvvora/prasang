"""Subscription/trial timers in Temporal's time-skipping server, with mocked activities."""
import uuid
from datetime import UTC, datetime, timedelta

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.workflows.subscription import SubscriptionWorkflow, TrialWorkflow

CALLS: list[tuple] = []


@activity.defn(name="expire_unpaid_subscription")
async def expire_unpaid(sub_id: str) -> None:
    CALLS.append(("expire", sub_id))


@activity.defn(name="lapse_subscription")
async def lapse(sub_id: str) -> None:
    CALLS.append(("lapse", sub_id))


@activity.defn(name="end_trial")
async def end_trial(artist_id: str) -> None:
    CALLS.append(("end_trial", artist_id))


ACTIVITIES = [expire_unpaid, lapse, end_trial]


async def _env_worker(env, queue):
    return Worker(env.client, task_queue=queue, workflows=[SubscriptionWorkflow, TrialWorkflow], activities=ACTIVITIES)


async def test_unpaid_checkout_expires_after_24h():
    CALLS.clear()
    queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env, await _env_worker(env, queue):
        result = await env.client.execute_workflow(SubscriptionWorkflow.run, "s1", id=f"sub-{uuid.uuid4()}", task_queue=queue)
    assert result == "expired" and CALLS == [("expire", "s1")]


async def test_active_subscription_lapses_without_renewal():
    CALLS.clear()
    queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env, await _env_worker(env, queue):
        handle = await env.client.start_workflow(SubscriptionWorkflow.run, "s2", id=f"sub-{uuid.uuid4()}", task_queue=queue)
        now = await env.get_current_time()
        await handle.signal(SubscriptionWorkflow.activated, (now + timedelta(days=30)).isoformat())
        await handle.signal(SubscriptionWorkflow.charged, (now + timedelta(days=60)).isoformat())
        assert await handle.result() == "lapsed"
        assert CALLS == [("lapse", "s2")]
        assert await env.get_current_time() >= now + timedelta(days=63)


async def test_cancelled_subscription_ends_without_lapse():
    CALLS.clear()
    queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env, await _env_worker(env, queue):
        handle = await env.client.start_workflow(SubscriptionWorkflow.run, "s3", id=f"sub-{uuid.uuid4()}", task_queue=queue)
        now = await env.get_current_time()
        await handle.signal(SubscriptionWorkflow.activated, (now + timedelta(days=30)).isoformat())
        await handle.signal(SubscriptionWorkflow.ended, "cancelled")
        assert await handle.result() == "cancelled"
    assert CALLS == []


async def test_trial_ends_after_its_end_time():
    CALLS.clear()
    queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env, await _env_worker(env, queue):
        ends = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        await env.client.execute_workflow(TrialWorkflow.run, args=["a1", ends], id=f"trial-{uuid.uuid4()}", task_queue=queue)
    assert CALLS == [("end_trial", "a1")]
