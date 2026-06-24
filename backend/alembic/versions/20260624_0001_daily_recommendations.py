"""add daily_recommendations and user nutrition goals

Revision ID: 20260624_0001
Revises: 20260623_0001
Create Date: 2026-06-24 10:00:00+08:00

新增 daily_recommendations 表，在 users 表新增 5 个营养/预算字段。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260624_0001'
down_revision: Union[str, None] = '20260623_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 daily_recommendations 表
    op.create_table(
        'daily_recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(20), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', 'meal_type', name='uq_user_date_meal'),
    )
    op.create_index(op.f('ix_daily_recommendations_id'), 'daily_recommendations', ['id'])

    # 2. 在 users 表新增 5 个字段
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('daily_calorie_target', sa.Float(), nullable=True, server_default='2000')
        )
        batch_op.add_column(
            sa.Column('daily_protein_target', sa.Float(), nullable=True, server_default='60')
        )
        batch_op.add_column(
            sa.Column('daily_carb_target', sa.Float(), nullable=True, server_default='300')
        )
        batch_op.add_column(
            sa.Column('daily_fat_target', sa.Float(), nullable=True, server_default='65')
        )
        batch_op.add_column(
            sa.Column('daily_budget', sa.Float(), nullable=True, server_default=None)
        )


def downgrade() -> None:
    op.drop_table('daily_recommendations')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('daily_budget')
        batch_op.drop_column('daily_fat_target')
        batch_op.drop_column('daily_carb_target')
        batch_op.drop_column('daily_protein_target')
        batch_op.drop_column('daily_calorie_target')
