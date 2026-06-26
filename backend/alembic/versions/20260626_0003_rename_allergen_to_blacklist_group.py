"""rename allergen_groups to blacklist_groups

Revision ID: 20260626_0003
Revises: 20260626_0002
Create Date: 2026-06-26 18:00:00+08:00

重命名过敏原分组相关表为原料黑名单分组（语义更准确：分组内容不限于过敏原）。
同时重命名 user_ingredient_blacklist 里的 allergen_group_id 列。
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260626_0003'
down_revision: Union[str, None] = '20260626_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 重命名三张表
    op.rename_table('allergen_groups', 'blacklist_groups')
    op.rename_table('allergen_group_ingredients', 'blacklist_group_ingredients')
    op.rename_table('user_allergen_group_blacklist', 'blacklist_group_subscriptions')

    # 重命名 user_ingredient_blacklist 里的外键列
    # 用 batch_alter_table 兼容 SQLite（旧版不支持直接 RENAME COLUMN）
    with op.batch_alter_table('user_ingredient_blacklist') as batch_op:
        batch_op.alter_column('allergen_group_id', new_column_name='blacklist_group_id')


def downgrade() -> None:
    with op.batch_alter_table('user_ingredient_blacklist') as batch_op:
        batch_op.alter_column('blacklist_group_id', new_column_name='allergen_group_id')

    op.rename_table('blacklist_group_subscriptions', 'user_allergen_group_blacklist')
    op.rename_table('blacklist_group_ingredients', 'allergen_group_ingredients')
    op.rename_table('blacklist_groups', 'allergen_groups')
