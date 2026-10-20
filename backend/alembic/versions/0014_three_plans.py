"""three plans: Basic (free), Pro, Premium — old Basic subscribers move to Pro

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-20

"""
from collections.abc import Sequence

from alembic import op

revision: str = '0014'
down_revision: str | Sequence[str] | None = '0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Old Basic (₹299, 5 photos + 1 video, 15 leads) is now Pro, so its artists and subscriptions move there.

    Postgres can't drop an enum value: 'basic' stays in subscription_tier, unused.
    """
    op.execute("UPDATE artist_profiles SET subscription_tier = 'pro' WHERE subscription_tier = 'basic'")
    op.execute("UPDATE subscriptions SET tier = 'pro' WHERE tier = 'basic'")
    op.execute("DELETE FROM subscription_plans WHERE tier = 'basic'")
    op.execute("UPDATE artist_profiles SET is_featured = featured_override WHERE subscription_tier <> 'premium'")
    op.execute("UPDATE artist_profiles SET search_boost_score = 10 WHERE subscription_tier = 'pro'")


def downgrade() -> None:
    """Data move only; nothing to undo structurally."""
