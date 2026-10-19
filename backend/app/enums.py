"""Postgres enum types shared by ORM models. Values mirror the contract Literals."""
from typing import get_args

from sqlalchemy import Enum

from app.contract import common as c


def _enum(literal, name: str) -> Enum:
    return Enum(*get_args(literal), name=name, native_enum=True, validate_strings=True)


ArtistTypeEnum = _enum(c.ArtistType, "artist_type")
EventTypeEnum = _enum(c.EventType, "event_type")
TierEnum = _enum(c.SubscriptionTier, "subscription_tier")
BudgetRangeEnum = _enum(c.BudgetRange, "budget_range")
LeadStatusEnum = _enum(c.LeadStatus, "lead_status")
LeadSourceEnum = _enum(c.LeadSource, "lead_source")
RoleEnum = _enum(c.Role, "user_role")
MediaKindEnum = Enum("image", "video", "youtube", "instagram", "facebook", name="media_kind")
TierSourceEnum = Enum("free", "trial", "paid", "grant", name="tier_source")
SubscriptionStatusEnum = Enum("created", "active", "halted", "cancelled", "completed", "expired", name="subscription_status")
BillingCycleEnum = _enum(c.BillingCycle, "billing_cycle")
