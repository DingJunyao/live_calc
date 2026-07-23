"""add image_tracking table

Revision ID: 20260723_0001
Revises: 20260721_0001
Create Date: 2026-07-23

"""
from alembic import op
import sqlalchemy as sa


revision = "20260723_0001"
down_revision = "20260721_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "image_tracking",
        sa.Column("key", sa.String(512), nullable=False),
        sa.Column("ref_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade():
    op.drop_table("image_tracking")
