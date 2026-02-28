"""Add is_imported field to Ingredient table

Revision ID: 1a2b3c4d5e6f
Revises:
Create Date: 2026-02-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add is_imported column to ingredients table
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.add_column(sa.Column('is_imported', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Remove is_imported column from ingredients table
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.drop_column('is_imported')