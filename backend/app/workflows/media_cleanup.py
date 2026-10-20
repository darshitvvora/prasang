"""DeleteMediaWorkflow: remove a deleted account's uploaded files from S3, retrying until storage cooperates."""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class DeleteMediaWorkflow:
    @workflow.run
    async def run(self, keys: list[str]) -> int:
        return await workflow.execute_activity("delete_media_files", keys, result_type=int,
                                               start_to_close_timeout=timedelta(minutes=2),
                                               retry_policy=RetryPolicy(initial_interval=timedelta(seconds=30), maximum_attempts=20))
