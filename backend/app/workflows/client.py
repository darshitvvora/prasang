"""Temporal client + the WorkflowStarter used by request handlers."""
import asyncio

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.config import get_settings

_client: Client | None = None
_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    global _client
    async with _lock:
        if _client is None:
            s = get_settings()
            _client = await Client.connect(s.temporal_address, namespace=s.temporal_namespace)
    return _client


class TemporalStarter:
    async def start_lead_notification(self, lead_id: str) -> None:
        from app.workflows.lead_notification import LeadNotificationWorkflow

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.start_workflow(LeadNotificationWorkflow.run, lead_id, id=f"lead-{lead_id}",
                                        task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass

    async def start_subscription(self, subscription_id: str) -> None:
        from app.workflows.subscription import SubscriptionWorkflow

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.start_workflow(SubscriptionWorkflow.run, args=[subscription_id, None], id=f"sub-{subscription_id}",
                                        task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass

    async def signal_subscription(self, subscription_id: str, signal: str, arg: str) -> None:
        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        await client.get_workflow_handle(f"sub-{subscription_id}").signal(signal, arg)

    async def start_trial(self, artist_id: str, ends_at_iso: str) -> None:
        from app.workflows.subscription import TrialWorkflow

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.start_workflow(TrialWorkflow.run, args=[artist_id, ends_at_iso], id=f"trial-{artist_id}",
                                        task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass

    async def start_message(self, message_id: str) -> None:
        from app.workflows.message import DeliverMessageWorkflow

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.start_workflow(DeliverMessageWorkflow.run, message_id, id=f"msg-{message_id}",
                                        task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass

    async def start_booking_followup(self, lead_id: str, inquiry_at_iso: str, event_date_iso: str | None) -> None:
        from app.workflows.booking_followup import BookingFollowUpWorkflow

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.start_workflow(BookingFollowUpWorkflow.run, args=[lead_id, inquiry_at_iso, event_date_iso],
                                        id=f"booking-{lead_id}", task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass

    async def signal_booking_settled(self, lead_id: str) -> None:
        from temporalio.service import RPCError

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.get_workflow_handle(f"booking-{lead_id}").signal("settled")
        except RPCError:  # already finished or never started (older lead): nothing to stop
            pass

    async def start_media_deletion(self, user_id: str, keys: list[str]) -> None:
        from app.workflows.media_cleanup import DeleteMediaWorkflow

        client = await asyncio.wait_for(get_temporal_client(), timeout=5)
        try:
            await client.start_workflow(DeleteMediaWorkflow.run, keys, id=f"delete-media-{user_id}",
                                        task_queue=get_settings().temporal_task_queue)
        except WorkflowAlreadyStartedError:
            pass
