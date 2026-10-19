"""Activities: everything with side effects (DB reads, sending messages)."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.artists.models import ArtistProfile
from app.auth.models import User
from app.leads.models import Lead
from app.notifications.notifier import NotificationRejected, Notifier
from app.subscriptions.models import SubscriptionPlan
from app.workflows.lead_notification import LeadContext, OutboundMessage

BUDGET_LABELS = {"5k_10k": "₹5K–10K", "10k_15k": "₹10K–15K", "15k_25k": "₹15K–25K", "25k_50k": "₹25K–50K", "50k_plus": "₹50K+"}


class LeadActivities:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], notifier: Notifier):
        self.sessions, self.notifier = sessions, notifier

    @activity.defn(name="load_lead_context")
    async def load_lead_context(self, lead_id: str) -> LeadContext:
        from app.labels import EVENT_TYPE_LABELS

        async with self.sessions() as s:
            lead = await s.get(Lead, lead_id)
            if lead is None:
                raise ApplicationError(f"lead {lead_id} not found", non_retryable=True)
            artist = await s.get(ArtistProfile, lead.artist_id)
            owner = await s.get(User, artist.user_id)
            plan = await s.get(SubscriptionPlan, artist.subscription_tier)
            return LeadContext(
                lead_id=lead_id, artist_name=artist.stage_name, artist_email=owner.email if owner else None,
                artist_phone=artist.contact_phone, artist_whatsapp=artist.whatsapp_number,
                whatsapp_enabled=plan.whatsapp_notifications, is_locked=lead.is_locked, planner_name=lead.planner_name,
                planner_phone=lead.planner_phone, event_title=EVENT_TYPE_LABELS[lead.event_type],
                event_date=lead.event_date.isoformat() if lead.event_date else None,
                budget_label=BUDGET_LABELS[lead.budget_range], notes=lead.notes)

    async def _send(self, fn, *args) -> None:
        try:
            await fn(*args)
        except NotificationRejected as err:
            raise ApplicationError(str(err), type="NotificationRejected", non_retryable=True) from err

    @activity.defn(name="send_email")
    async def send_email(self, msg: OutboundMessage) -> None:
        await self._send(self.notifier.send_email, msg.to, msg.subject, msg.text)

    @activity.defn(name="send_whatsapp")
    async def send_whatsapp(self, msg: OutboundMessage) -> None:
        await self._send(self.notifier.send_whatsapp, msg.to, msg.text)

    @activity.defn(name="send_sms")
    async def send_sms(self, msg: OutboundMessage) -> None:
        await self._send(self.notifier.send_sms, msg.to, msg.text)

    def all(self) -> list:
        return [self.load_lead_context, self.send_email, self.send_whatsapp, self.send_sms]


class SubscriptionActivities:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], gateway):
        self.sessions, self.gateway = sessions, gateway

    @activity.defn(name="expire_unpaid_subscription")
    async def expire_unpaid_subscription(self, subscription_id: str) -> None:
        from app.subscriptions.service import expire_unpaid

        async with self.sessions() as s:
            await expire_unpaid(s, subscription_id, self.gateway)

    @activity.defn(name="lapse_subscription")
    async def lapse_subscription(self, subscription_id: str) -> None:
        from app.subscriptions.service import lapse

        async with self.sessions() as s:
            await lapse(s, subscription_id)

    @activity.defn(name="end_trial")
    async def end_trial(self, artist_id: str) -> None:
        from app.subscriptions.service import end_trial

        async with self.sessions() as s:
            await end_trial(s, artist_id)

    def all(self) -> list:
        return [self.expire_unpaid_subscription, self.lapse_subscription, self.end_trial]
