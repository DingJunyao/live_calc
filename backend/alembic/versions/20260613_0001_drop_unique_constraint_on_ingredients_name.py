"""drop unique constraint on ingredients.name

Revision ID: 20260613_0001
Revises: 20260611_0001
Create Date: 2026-06-13 10:00:00.000000

将 ingredients.name 的唯一索引降级为普通索引，使软删除(is_active=False)
的原料不再占用 name，从而允许删除后新建同名原料。
"""
from alembic import op

revision = '20260613_0001'
down_revision = '20260611_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_ingredients_name', table_name='ingredients')
    op.create_index('ix_ingredients_name', 'ingredients', ['name'], unique=False)


def downgrade():
    op.drop_index('ix_ingredients_name', table_name='ingredients')
    op.create_index('ix_ingredients_name', 'ingredients', ['name'], unique=True)
