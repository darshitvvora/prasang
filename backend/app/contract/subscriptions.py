from datetime import date
from typing import Literal

from pydantic import ConfigDict

from app.contract.common import BillingCycle, ContractModel, PaidTier, SubscriptionTier


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


class MySubscriptionResponse(ContractModel):
    plan: PlanUsage
    subscription: SubscriptionSummary | None


class CreateSubscriptionRequest(ContractModel):
    tier: PaidTier
    billing_cycle: BillingCycle


class CheckoutPrefill(ContractModel):
    name: str
    email: str | None
    contact: str | None


class Checkout(ContractModel):
    key_id: str
    razorpay_subscription_id: str
    name: str
    description: str
    prefill: CheckoutPrefill


class CreateSubscriptionResponse(ContractModel):
    subscription_id: str
    checkout: Checkout


class VerifyPaymentRequest(ContractModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


class VerifyPaymentResponse(ContractModel):
    status: Literal["active", "pending_activation"]
    plan: PlanUsage


class StartTrialRequest(ContractModel):
    tier: PaidTier


class RazorpayWebhookEvent(ContractModel):
    """Razorpay's own payload — only the fields we route on are declared; the rest is kept as-is."""

    model_config = ConfigDict(extra="allow")
    event: str
    payload: dict
