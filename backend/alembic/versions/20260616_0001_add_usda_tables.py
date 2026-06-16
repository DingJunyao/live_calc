"""add usda tables

Revision ID: 20260616_0001
Revises: 20260615_0001
Create Date: 2026-06-16 10:00:00.000000

新增 USDA 营养数据仓库：usda_foods / usda_food_nutrients /
translation_configs / usda_tasks，用于原料/商品手动匹配 USDA 营养素。
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260616_0001'
down_revision: Union[str, None] = '20260615_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usda_foods',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('fdc_id', sa.Integer(), nullable=False),
        sa.Column('data_type', sa.String(32), nullable=False),
        sa.Column('description', sa.String(512), nullable=False),
        sa.Column('description_zh', sa.String(512), nullable=True),
        sa.Column('translate_status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('publication_date', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('fdc_id', name='uq_usda_foods_fdc_id'),
    )
    op.create_index('ix_usda_foods_fdc_id', 'usda_foods', ['fdc_id'])
    op.create_index('ix_usda_foods_data_type', 'usda_foods', ['data_type'])
    op.create_index('ix_usda_foods_description', 'usda_foods', ['description'])
    op.create_index('ix_usda_foods_description_zh', 'usda_foods', ['description_zh'])

    op.create_table(
        'usda_food_nutrients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('fdc_id', sa.Integer(), nullable=False),
        sa.Column('nutrient_no', sa.String(16), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_zh', sa.String(255), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('unit_name', sa.String(32), nullable=False),
    )
    op.create_index('ix_usda_food_nutrients_fdc_id', 'usda_food_nutrients', ['fdc_id'])

    op.create_table(
        'translation_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'usda_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('task_type', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('progress', sa.JSON(), nullable=True),
        sa.Column('provider', sa.String(32), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_usda_tasks_task_type', 'usda_tasks', ['task_type'])


def downgrade() -> None:
    op.drop_index('ix_usda_tasks_task_type', table_name='usda_tasks')
    op.drop_table('usda_tasks')
    op.drop_table('translation_configs')
    op.drop_index('ix_usda_food_nutrients_fdc_id', table_name='usda_food_nutrients')
    op.drop_table('usda_food_nutrients')
    op.drop_index('ix_usda_foods_description_zh', table_name='usda_foods')
    op.drop_index('ix_usda_foods_description', table_name='usda_foods')
    op.drop_index('ix_usda_foods_data_type', table_name='usda_foods')
    op.drop_index('ix_usda_foods_fdc_id', table_name='usda_foods')
    op.drop_table('usda_foods')
