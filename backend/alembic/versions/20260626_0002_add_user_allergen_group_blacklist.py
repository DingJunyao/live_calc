"""add user_allergen_group_blacklist table

Revision ID: 20260626_0002
Revises: 20260626_0001
Create Date: 2026-06-26 16:00:00+08:00

新增用户过敏原分组订阅表，支持动态黑名单。
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260626_0002'
down_revision: Union[str, None] = '20260626_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_allergen_group_blacklist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('allergen_group_id', sa.Integer(), sa.ForeignKey('allergen_groups.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'allergen_group_id', name='uq_user_allergen_group_blacklist'),
    )
    op.create_index('ix_user_ag_blacklist_user', 'user_allergen_group_blacklist', ['user_id'])
    op.create_index('ix_user_ag_blacklist_group', 'user_allergen_group_blacklist', ['allergen_group_id'])


def downgrade() -> None:
    op.drop_table('user_allergen_group_blacklist')
