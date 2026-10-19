"""Temporal worker process: `python -m app.workflows.worker`."""
import asyncio
import logging

from temporalio.worker import Worker

import app.models  # noqa: F401
from app.config import get_settings
from app.db import get_sessionmaker
from app.notifications.notifier import get_notifier
from app.workflows.activities import LeadActivities
from app.workflows.client import get_temporal_client
from app.workflows.lead_notification import LeadNotificationWorkflow

log = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    client = await get_temporal_client()
    activities = LeadActivities(get_sessionmaker(), get_notifier(settings))
    worker = Worker(client, task_queue=settings.temporal_task_queue, workflows=[LeadNotificationWorkflow], activities=activities.all())
    log.info("worker polling task queue %s", settings.temporal_task_queue)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
