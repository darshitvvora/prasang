"""How request handlers kick off durable workflows. Swapped for the Temporal implementation in app.workflows.client."""
import logging
from typing import Protocol

log = logging.getLogger(__name__)


class WorkflowStarter(Protocol):
    async def start_lead_notification(self, lead_id: str) -> None: ...
    async def start_subscription(self, subscription_id: str, pay_by_iso: str) -> None: ...
    async def signal_subscription(self, subscription_id: str, signal: str, arg: str) -> None: ...
    async def start_trial(self, artist_id: str, ends_at_iso: str) -> None: ...
    async def start_message(self, message_id: str) -> None: ...
    async def start_booking_followup(self, lead_id: str, inquiry_at_iso: str, event_date_iso: str | None) -> None: ...
    async def signal_booking_settled(self, lead_id: str) -> None: ...
    async def start_media_deletion(self, user_id: str, keys: list[str]) -> None: ...


class NoopStarter:
    async def start_lead_notification(self, lead_id: str) -> None:
        log.info("lead %s created (workflows disabled)", lead_id)

    async def start_subscription(self, subscription_id: str, pay_by_iso: str) -> None:
        log.info("subscription %s awaiting payment until %s (workflows disabled)", subscription_id, pay_by_iso)

    async def signal_subscription(self, subscription_id: str, signal: str, arg: str) -> None:
        log.info("subscription %s: %s %s (workflows disabled)", subscription_id, signal, arg)

    async def start_trial(self, artist_id: str, ends_at_iso: str) -> None:
        log.info("trial for %s until %s (workflows disabled)", artist_id, ends_at_iso)

    async def start_message(self, message_id: str) -> None:
        log.info("message %s queued (workflows disabled)", message_id)

    async def start_booking_followup(self, lead_id: str, inquiry_at_iso: str, event_date_iso: str | None) -> None:
        log.info("booking follow-up for %s (workflows disabled)", lead_id)

    async def signal_booking_settled(self, lead_id: str) -> None:
        log.info("booking %s settled (workflows disabled)", lead_id)

    async def start_media_deletion(self, user_id: str, keys: list[str]) -> None:
        log.info("media deletion for %s: %d files (workflows disabled)", user_id, len(keys))


_starter: WorkflowStarter = NoopStarter()


def set_starter(starter: WorkflowStarter) -> None:
    global _starter
    _starter = starter


def get_starter() -> WorkflowStarter:
    return _starter
