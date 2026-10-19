"""Temporal worker process: `python -m app.workflows.worker`."""
import asyncio
import logging

from temporalio.worker import Worker

import app.models  # noqa: F401
from app.config import get_settings
from app.db import get_sessionmaker
from app.notifications.notifier import get_notifier
from app.subscriptions.gateway import get_gateway
from app.workflows.activities import BookingActivities, LeadActivities, MessageActivities, SubscriptionActivities
from app.workflows.booking_followup import BookingFollowUpWorkflow
from app.workflows.client import get_temporal_client
from app.workflows.lead_notification import LeadNotificationWorkflow
from app.workflows.message import DeliverMessageWorkflow
from app.workflows.subscription import SubscriptionWorkflow, TrialWorkflow

log = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    client = await get_temporal_client()
    sessions = get_sessionmaker()
    notifier = get_notifier(settings)
    activities = (LeadActivities(sessions, notifier).all() + SubscriptionActivities(sessions, get_gateway()).all()
                  + MessageActivities(sessions, notifier).all() + BookingActivities(sessions).all())
    workflows = [LeadNotificationWorkflow, SubscriptionWorkflow, TrialWorkflow, DeliverMessageWorkflow, BookingFollowUpWorkflow]
    worker = Worker(client, task_queue=settings.temporal_task_queue, workflows=workflows, activities=activities)
    log.info("worker polling task queue %s", settings.temporal_task_queue)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
