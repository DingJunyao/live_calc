"""add picgo fields to storage_configurations

Revision ID: 20260721_0001
Revises: 20260720_0004
Create Date: 2026-07-21

- add s3_base_path column (key prefix, e.g., "livecalc/")
- add s3_custom_domain column (custom domain, e.g., "https://cdn.example.com")
- add s3_url_suffix column (URL suffix, e.g., "?imageslim")
"""
from alembic import op
import sqlalchemy as sa


revision = "20260721_0001"
down_revision = "20260720_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("storage_configurations", sa.Column("s3_base_path", sa.String(255), nullable=True))
    op.add_column("storage_configurations", sa.Column("s3_custom_domain", sa.String(255), nullable=True))
    op.add_column("storage_configurations", sa.Column("s3_url_suffix", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("storage_configurations", "s3_url_suffix")
    op.drop_column("storage_configurations", "s3_custom_domain")
    op.drop_column("storage_configurations", "s3_base_path")
