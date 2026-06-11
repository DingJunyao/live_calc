"""add is_active to product_records

Revision ID: 20260611_0001
Revises: 20260609_0001_add_is_open_to_merchants
Create Date: 2026-06-11 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260611_0001'
down_revision = '20260609_0001_add_is_open_to_merchants'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('product_records', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))


def downgrade():
    op.drop_column('product_records', 'is_active')
