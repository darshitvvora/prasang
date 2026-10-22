"""PhonePe payment links replace Razorpay subscriptions: each subscription row is one paid period with its own link

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-22

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0015'
down_revision: str | Sequence[str] | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Razorpay plan ids are gone; open Razorpay checkouts can't be paid any more, so they expire."""
    op.add_column('subscriptions', sa.Column('payment_url', sa.String(length=300), nullable=True))
    op.add_column('subscriptions', sa.Column('pay_by', sa.DateTime(timezone=True), nullable=True))
    op.add_column('subscriptions', sa.Column('renews_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('subscriptions_renews_id_fkey', 'subscriptions', 'subscriptions', ['renews_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_subscriptions_renews_id', 'subscriptions', ['renews_id'])
    op.execute("UPDATE subscriptions SET status = 'expired' WHERE status = 'created'")
    op.drop_column('subscription_plans', 'gateway_plan_annual')
    op.drop_column('subscription_plans', 'gateway_plan_monthly')


def downgrade() -> None:
    op.add_column('subscription_plans', sa.Column('gateway_plan_monthly', sa.String(length=60), nullable=True))
    op.add_column('subscription_plans', sa.Column('gateway_plan_annual', sa.String(length=60), nullable=True))
    op.drop_index('ix_subscriptions_renews_id', table_name='subscriptions')
    op.drop_constraint('subscriptions_renews_id_fkey', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'renews_id')
    op.drop_column('subscriptions', 'pay_by')
    op.drop_column('subscriptions', 'payment_url')
