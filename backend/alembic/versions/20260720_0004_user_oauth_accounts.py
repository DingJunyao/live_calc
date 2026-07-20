"""Create user_oauth_accounts table — OAuth provider framework reservation

Revision ID: 20260720_0004
Revises: 20260720_0003
Create Date: 2026-07-20

- create user_oauth_accounts table
- unique constraint on (provider, provider_user_id)
- index on unionid for WeChat cross-app lookup
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_0004"
down_revision = "20260720_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_oauth_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=128), nullable=False),
        sa.Column("unionid", sa.String(length=128), nullable=True),
        sa.Column("access_token", sa.String(length=512), nullable=True),
        sa.Column("refresh_token", sa.String(length=512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_oauth_unionid", "user_oauth_accounts", ["unionid"])
    op.create_unique_constraint(
        "uq_provider_user",
        "user_oauth_accounts",
        ["provider", "provider_user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_provider_user", "user_oauth_accounts")
    op.drop_index("ix_oauth_unionid", table_name="user_oauth_accounts")
    op.drop_table("user_oauth_accounts")
