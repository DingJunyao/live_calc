"""add storage_configurations table

Revision ID: 20260720_0002
Revises: 20260720_0004
Create Date: 2026-07-20

"""
from alembic import op
import sqlalchemy as sa

revision = "20260720_0002"
down_revision = "20260720_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "storage_configurations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("backend", sa.String(10), nullable=False, server_default="local"),
        sa.Column("storage_base_url", sa.String(255), nullable=True),
        sa.Column("s3_endpoint", sa.String(255), nullable=True),
        sa.Column("s3_access_key", sa.String(255), nullable=True),
        sa.Column("s3_secret_key", sa.String(255), nullable=True),
        sa.Column("s3_bucket", sa.String(255), nullable=True),
        sa.Column("s3_region", sa.String(64), nullable=True),
        sa.Column("s3_url_style", sa.String(10), nullable=False, server_default="path"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("storage_configurations")
