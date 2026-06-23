"""add user_merchant_product_orders table

Revision ID: 20260623_0001
Revises: 20260622_0003
Create Date: 2026-06-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260623_0001"
down_revision: Union[str, None] = "20260622_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_merchant_product_orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("merchant_id", sa.Integer(), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"],),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"],),
        sa.UniqueConstraint(
            "user_id", "merchant_id", "product_id", "session_date",
            name="uq_umpo_user_merchant_product_date",
        ),
    )
    op.create_index(
        "idx_umpo_lookup",
        "user_merchant_product_orders",
        ["user_id", "merchant_id", "session_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_umpo_lookup", table_name="user_merchant_product_orders")
    op.drop_table("user_merchant_product_orders")
