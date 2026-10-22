"""LeadNotificationWorkflow: tell the artist about a new lead on every channel their plan allows.

Workflow code only (deterministic). Activities live in app.workflows.activities and are referenced by name.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), backoff_coefficient=2, maximum_attempts=3,
                    non_retryable_error_types=["NotificationRejected"])
TIMEOUT = timedelta(seconds=30)


@dataclass
class LeadContext:
    lead_id: str
    artist_name: str
    artist_email: str | None
    artist_phone: str
    artist_whatsapp: str | None
    whatsapp_enabled: bool
    is_locked: bool
    planner_name: str
    planner_phone: str
    event_title: str
    event_date: str | None
    budget_label: str
    notes: str | None


@dataclass
class OutboundMessage:
    to: str
    text: str
    subject: str = ""
    kind: str = ""  # SMS/WhatsApp template kind (app.notifications.texts) and its variables
    variables: dict[str, str] = field(default_factory=dict)


def _when(c: LeadContext) -> str:
    return date.fromisoformat(c.event_date).strftime("%-d %b %Y") if c.event_date else "date not fixed yet"


def lead_text_message(c: LeadContext) -> tuple[str, dict[str, str]]:
    """SMS/WhatsApp template kind + variables (a locked lead hides the planner's details)."""
    common = {"event": c.event_title, "date": _when(c), "budget": c.budget_label}
    if c.is_locked:
        return "lead_locked", common | {"link": "https://prasang.in/pricing"}
    return "lead", common | {"planner": c.planner_name, "phone": c.planner_phone, "link": "https://prasang.in/artist/leads"}


def lead_message(c: LeadContext) -> str:
    when = _when(c)
    if c.is_locked:
        return (f"New lead on Prasang: someone wants to book you for a {c.event_title} ({when}, {c.budget_label}). "
                "You've reached this month's lead limit — upgrade your plan to see their details: https://prasang.in/pricing")
    lines = [f"New lead on Prasang! {c.planner_name} wants to book you for a {c.event_title} on {when}.",
             f"Budget: {c.budget_label}. Call them: +91 {c.planner_phone}"]
    if c.notes:
        lines.append(f"Notes: {c.notes}")
    lines.append("See all leads: https://prasang.in/artist/leads")
    return "\n".join(lines)


@workflow.defn
class LeadNotificationWorkflow:
    @workflow.run
    async def run(self, lead_id: str) -> dict:
        ctx: LeadContext = await workflow.execute_activity(
            "load_lead_context", lead_id, result_type=LeadContext, start_to_close_timeout=TIMEOUT, retry_policy=RETRY)
        text = lead_message(ctx)
        kind, variables = lead_text_message(ctx)
        sent = {"email": False, "whatsapp": False, "sms": False}

        async def attempt(channel: str, msg: OutboundMessage) -> None:
            try:
                await workflow.execute_activity(f"send_{channel}", msg, start_to_close_timeout=TIMEOUT, retry_policy=RETRY)
                sent[channel] = True
            except Exception as err:  # one channel failing must not stop the others
                workflow.logger.warning("lead %s: %s notification failed: %s", lead_id, channel, err)

        if ctx.artist_email:
            await attempt("email", OutboundMessage(to=ctx.artist_email, text=text, subject=f"New lead: {ctx.event_title}"))
        if ctx.whatsapp_enabled:
            await attempt("whatsapp", OutboundMessage(to=ctx.artist_whatsapp or ctx.artist_phone, text=text, kind=kind,
                                                      variables=variables))
        if not sent["whatsapp"]:
            await attempt("sms", OutboundMessage(to=ctx.artist_phone, text=text, kind=kind, variables=variables))
        return sent
