"""add user_ingredient_blacklist, allergen_groups, allergen_group_ingredients tables

Revision ID: 20260626_0001
Revises: 20260624_0001
Create Date: 2026-06-26 10:00:00+08:00

新增用户原料黑名单表和过敏原分组相关表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260626_0001'
down_revision: Union[str, None] = '20260624_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. allergen_groups
    op.create_table(
        'allergen_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_allergen_groups_is_active'), 'allergen_groups', ['is_active'])

    # 2. allergen_group_ingredients
    op.create_table(
        'allergen_group_ingredients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('allergen_groups.id'), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), sa.ForeignKey('ingredients.id'), nullable=False),
        sa.Column('is_ai_matched', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'ingredient_id', name='uq_allergen_group_ingredient'),
    )
    op.create_index(op.f('ix_allergen_group_ingredients_group_id'), 'allergen_group_ingredients', ['group_id'])
    op.create_index(op.f('ix_allergen_group_ingredients_ingredient_id'), 'allergen_group_ingredients', ['ingredient_id'])

    # 3. user_ingredient_blacklist
    op.create_table(
        'user_ingredient_blacklist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), sa.ForeignKey('ingredients.id'), nullable=False),
        sa.Column('reason', sa.String(100), nullable=True),
        sa.Column('source', sa.String(50), server_default='manual', nullable=False),
        sa.Column('allergen_group_id', sa.Integer(), sa.ForeignKey('allergen_groups.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'ingredient_id', name='uq_user_ingredient_blacklist'),
    )
    op.create_index(op.f('ix_user_ingredient_blacklist_user_id'), 'user_ingredient_blacklist', ['user_id'])
    op.create_index(op.f('ix_user_ingredient_blacklist_ingredient_id'), 'user_ingredient_blacklist', ['ingredient_id'])
    op.create_index(op.f('ix_blacklist_allergen_group'), 'user_ingredient_blacklist', ['allergen_group_id'])


def downgrade() -> None:
    op.drop_table('user_ingredient_blacklist')
    op.drop_table('allergen_group_ingredients')
    op.drop_table('allergen_groups')
