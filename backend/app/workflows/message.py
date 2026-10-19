"""DeliverMessageWorkflow: send one queued outbound message (app.notifications.queue). Workflow id `msg-{message_id}`."""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

RETRY = RetryPolicy(initial_interval=timedelta(seconds=5), backoff_coefficient=2, maximum_attempts=5)


@workflow.defn
class DeliverMessageWorkflow:
    @workflow.run
    async def run(self, message_id: str) -> str:
        return await workflow.execute_activity("deliver_message", message_id, result_type=str,
                                               start_to_close_timeout=timedelta(seconds=60), retry_policy=RETRY)
