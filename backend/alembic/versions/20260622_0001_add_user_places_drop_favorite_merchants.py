"""add user_places and drop legacy favorite_merchants

Revision ID: 20260622_0001
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 10:00:00+08:00

- 新建 user_places：用户常用地点（家/公司等），供商家管理地图默认聚焦。
- 删除遗留的 favorite_merchants 表（前端从未接入、被 user_places 取代）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260622_0001'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 创建 user_places 表
    op.create_table(
        'user_places',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False, server_default='custom'),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('view_radius_km', sa.Numeric(precision=10, scale=2), nullable=False, server_default='5'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_places_id'), 'user_places', ['id'], unique=False)
    op.create_index(op.f('ix_user_places_user_id'), 'user_places', ['user_id'], unique=False)

    # 2) 删除遗留的 favorite_merchants 表
    op.drop_table('favorite_merchants')


def downgrade() -> None:
    # 1) 重建 favorite_merchants（含原 model 字段 + 20260320 加的 audit 字段，保 downgrade 链完整）
    op.create_table(
        'favorite_merchants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True, server_default='other'),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        # 20260320 审计字段
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_favorite_merchants_id'), 'favorite_merchants', ['id'], unique=False)
    op.create_index(op.f('ix_favorite_merchants_user_id'), 'favorite_merchants', ['user_id'], unique=False)

    # 2) 删除 user_places
    op.drop_table('user_places')
