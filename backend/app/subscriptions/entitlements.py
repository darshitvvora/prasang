"""What each plan unlocks beyond the numbers on the pricing page (decided 2026-10-20).

Photo/video counts live in subscription_plans (seeded from contracts/examples/subscriptions/plans.response.json);
these flags drive ranking, embeds, the badge and HD uploads.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Entitlements:
    search_boost_score: int
    is_featured: bool
    whatsapp_notifications: bool
    social_embeds: bool  # Instagram/YouTube/Facebook embeds + profile widgets (Free: text links only)
    verified_badge: bool  # badge shows when the plan allows it AND an admin verified the artist


ENTITLEMENTS: dict[str, Entitlements] = {
    "free": Entitlements(search_boost_score=0, is_featured=False, whatsapp_notifications=False, social_embeds=False, verified_badge=False),
    "basic": Entitlements(search_boost_score=10, is_featured=False, whatsapp_notifications=True, social_embeds=True, verified_badge=False),
    "pro": Entitlements(search_boost_score=25, is_featured=False, whatsapp_notifications=True, social_embeds=True, verified_badge=True),
    "premium": Entitlements(search_boost_score=50, is_featured=True, whatsapp_notifications=True, social_embeds=True, verified_badge=True),
}

EMBED_KINDS = ("youtube", "instagram", "facebook")


def for_tier(tier: str) -> Entitlements:
    return ENTITLEMENTS[tier]
