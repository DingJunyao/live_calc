"""add map_enabled to map_configurations

Revision ID: 20260719_0001
Revises:
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa


revision = '20260719_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'map_configurations',
        sa.Column(
            'map_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )


def downgrade() -> None:
    op.drop_column('map_configurations', 'map_enabled')
