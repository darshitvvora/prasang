import uuid

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.workflows.message import DeliverMessageWorkflow

CALLS: list[str] = []


@activity.defn(name="deliver_message")
async def deliver_message(message_id: str) -> str:
    CALLS.append(message_id)
    return "sent"


async def test_deliver_message_workflow_calls_activity_once():
    CALLS.clear()
    queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env, Worker(
            env.client, task_queue=queue, workflows=[DeliverMessageWorkflow], activities=[deliver_message]):
        result = await env.client.execute_workflow(DeliverMessageWorkflow.run, "m1", id=f"msg-{uuid.uuid4()}", task_queue=queue)
    assert result == "sent" and CALLS == ["m1"]
