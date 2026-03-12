"""add custom nutrition fields to products

Revision ID: add_custom_nutrition
Revises: 20260312_add_fields_for_ingredient_merge_functionality
Create Date: 2026-03-12 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_custom_nutrition'
down_revision = '20260312_add_fields_for_ingredient_merge_functionality'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加自定义营养数据字段
    op.add_column('products', sa.Column(
        'custom_nutrition_data',
        sa.JSON(),
        nullable=True
    ))
    op.add_column('products', sa.Column(
        'custom_nutrition_source',
        sa.String(50),
        nullable=True,
        server_default='custom'
    ))


def downgrade() -> None:
    op.drop_column('products', 'custom_nutrition_source')
    op.drop_column('products', 'custom_nutrition_data')