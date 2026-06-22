"""add system_config and enhance invite_codes (used→used_count + max_uses)

Revision ID: 20260622_0002
Revises: 20260622_0001
Create Date: 2026-06-22 16:00:00+08:00

- 新建 system_config：动态系统配置键值表
- invite_codes：used 改名 used_count + 新增 max_uses（可选次数限制）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260622_0002'
down_revision: Union[str, None] = '20260622_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 创建 system_config 表
    op.create_table(
        'system_config',
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('key'),
    )

    # 2) invite_codes：used → used_count
    with op.batch_alter_table('invite_codes') as batch_op:
        batch_op.alter_column('used', new_column_name='used_count',
                              existing_type=sa.Boolean(),
                              type_=sa.Integer(),
                              existing_nullable=False,
                              server_default='0')
        batch_op.add_column(sa.Column('max_uses', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('invite_codes') as batch_op:
        batch_op.drop_column('max_uses')
        batch_op.alter_column('used_count', new_column_name='used',
                              existing_type=sa.Integer(),
                              type_=sa.Boolean(),
                              existing_nullable=False,
                              server_default=None)

    op.drop_table('system_config')
