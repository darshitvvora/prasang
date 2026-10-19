"""How request handlers kick off durable workflows. Swapped for the Temporal implementation in app.workflows.client."""
import logging
from typing import Protocol

log = logging.getLogger(__name__)


class WorkflowStarter(Protocol):
    async def start_lead_notification(self, lead_id: str) -> None: ...


class NoopStarter:
    async def start_lead_notification(self, lead_id: str) -> None:
        log.info("lead %s created (workflows disabled)", lead_id)


_starter: WorkflowStarter = NoopStarter()


def set_starter(starter: WorkflowStarter) -> None:
    global _starter
    _starter = starter


def get_starter() -> WorkflowStarter:
    return _starter
