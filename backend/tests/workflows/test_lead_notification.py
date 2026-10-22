"""LeadNotificationWorkflow with mocked activities in Temporal's time-skipping test server."""
import uuid

import pytest
from temporalio import activity
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.workflows.lead_notification import LeadContext, LeadNotificationWorkflow, OutboundMessage

SENT: list[tuple[str, str]] = []
FAIL_WHATSAPP = {"on": False}


def ctx(**kw) -> LeadContext:
    base = dict(lead_id="l1", artist_name="Arjun", artist_email="arjun@example.com", artist_phone="9820011001",
                artist_whatsapp="9820011001", whatsapp_enabled=True, is_locked=False, planner_name="Neha",
                planner_phone="9920012345", event_title="Wedding", event_date="2026-12-12", budget_label="₹15K–25K", notes=None)
    return LeadContext(**(base | kw))


CURRENT = {"ctx": ctx()}


@activity.defn(name="load_lead_context")
async def load_lead_context(lead_id: str) -> LeadContext:
    return CURRENT["ctx"]


@activity.defn(name="send_email")
async def send_email(msg: OutboundMessage) -> None:
    SENT.append(("email", msg.to))


@activity.defn(name="send_whatsapp")
async def send_whatsapp(msg: OutboundMessage) -> None:
    if FAIL_WHATSAPP["on"]:
        raise ApplicationError("whatsapp template rejected", non_retryable=True, type="NotificationRejected")
    SENT.append(("whatsapp", msg.to))


@activity.defn(name="send_sms")
async def send_sms(msg: OutboundMessage) -> None:
    SENT.append(("sms", msg.to))


async def _run(context: LeadContext) -> dict:
    SENT.clear()
    CURRENT["ctx"] = context
    queue = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env, Worker(
        env.client, task_queue=queue, workflows=[LeadNotificationWorkflow],
        activities=[load_lead_context, send_email, send_whatsapp, send_sms],
    ):
        return await env.client.execute_workflow(LeadNotificationWorkflow.run, "l1", id=f"lead-{uuid.uuid4()}", task_queue=queue)


@pytest.fixture(autouse=True)
def _reset():
    FAIL_WHATSAPP["on"] = False


async def test_paid_tier_gets_email_and_whatsapp():
    result = await _run(ctx())
    assert sorted(SENT) == [("email", "arjun@example.com"), ("whatsapp", "9820011001")]
    assert result == {"email": True, "whatsapp": True, "sms": False}


async def test_free_tier_gets_email_and_sms():
    await _run(ctx(whatsapp_enabled=False))
    assert sorted(SENT) == [("email", "arjun@example.com"), ("sms", "9820011001")]


async def test_whatsapp_failure_falls_back_to_sms():
    FAIL_WHATSAPP["on"] = True
    result = await _run(ctx())
    assert ("sms", "9820011001") in SENT and result["whatsapp"] is False


async def test_artist_without_email_still_gets_a_text():
    await _run(ctx(artist_email=None, whatsapp_enabled=False))
    assert SENT == [("sms", "9820011001")]


def test_lead_texts_fill_their_msg91_templates():
    from app.notifications.texts import TextMessage
    from app.workflows.lead_notification import lead_text_message

    open_lead = TextMessage(*lead_text_message(ctx()))
    assert open_lead.kind == "lead" and "9920012345" in open_lead.text and "12 Dec 2026" in open_lead.text
    locked = TextMessage(*lead_text_message(ctx(is_locked=True, event_date=None)))
    assert locked.kind == "lead_locked" and "9920012345" not in locked.text  # over the limit: no planner details
