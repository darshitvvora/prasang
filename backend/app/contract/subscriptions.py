from datetime import date
from typing import Literal

from pydantic import ConfigDict

from app.contract.common import BillingCycle, ContractModel, PaidTier, SubscriptionTier, UtcDatetime


class PlanUsage(ContractModel):
    tier: SubscriptionTier
    name: str
    status: Literal["free", "trial", "active", "cancelling", "halted"]
    lead_limit_monthly: int
    leads_used_this_month: int
    leads_remaining: int | None
    period_end: date | None
    trial_ends_at: date | None
    trial_available: bool


class PlanFeature(ContractModel):
    label: str
    value: bool | str


class Plan(ContractModel):
    tier: SubscriptionTier
    name: str
    tagline: str
    monthly_price: int
    annual_price: int
    annual_monthly_equivalent: int
    lead_limit_monthly: int
    max_images: int
    max_videos: int
    max_hd_videos: int
    popular: bool
    features: list[PlanFeature]


class PlanList(ContractModel):
    items: list[Plan]


class SubscriptionSummary(ContractModel):
    id: str
    tier: SubscriptionTier
    billing_cycle: BillingCycle
    status: Literal["created", "active", "halted", "cancelled", "completed", "expired"]
    current_period_end: date | None
    cancel_at_period_end: bool


class PaymentLinkInfo(ContractModel):
    """A PhonePe payment link (also emailed and texted to the artist). Pay once; the plan starts when PhonePe confirms."""

    url: str
    expires_at: UtcDatetime
    amount: int  # rupees


class PendingPayment(ContractModel):
    """An unpaid link: a renewal (sent 5 days before the period ends) or a purchase/plan change not paid yet."""

    subscription_id: str
    tier: PaidTier
    billing_cycle: BillingCycle
    renewal: bool
    payment: PaymentLinkInfo


class MySubscriptionResponse(ContractModel):
    plan: PlanUsage
    subscription: SubscriptionSummary | None
    pending_payment: PendingPayment | None


class CreateSubscriptionRequest(ContractModel):
    tier: PaidTier
    billing_cycle: BillingCycle


class CreateSubscriptionResponse(ContractModel):
    subscription_id: str
    payment: PaymentLinkInfo


class VerifyPaymentRequest(ContractModel):
    """The artist says they paid: the server asks PhonePe for the link's status (the webhook usually got there first)."""

    subscription_id: str


class VerifyPaymentResponse(ContractModel):
    status: Literal["active", "pending_activation"]
    plan: PlanUsage


class StartTrialRequest(ContractModel):
    tier: PaidTier


class PhonePeWebhookEvent(ContractModel):
    """PhonePe's own payload (`paylink.order.completed` / `paylink.order.failed`) — only the routing fields are declared."""

    model_config = ConfigDict(extra="allow")
    event: str
    payload: dict


class BillingItem(ContractModel):
    id: str
    paid_at: UtcDatetime
    tier: PaidTier
    billing_cycle: BillingCycle
    amount: int  # rupees
    currency: str
    status: Literal["paid", "failed"]
    receipt_url: str | None


class BillingHistoryResponse(ContractModel):
    items: list[BillingItem]


class DowngradePreview(ContractModel):
    tier: SubscriptionTier
    photos: int
    videos: int
    hd_videos: int
    embeds: int
