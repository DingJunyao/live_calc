"""add token_version to users

Revision ID: 20260622_0003
Revises: 20260622_0002
Create Date: 2026-06-22 18:00:00+08:00

重置密码作废旧 token：users 新增 token_version（Integer, default 0, not null）。
存量用户填 0；存量老 token 无 ver claim，校验时取默认 0，与库中 0 相等，不受影响。
管理员重置某用户密码时 token_version += 1，该用户所有旧 token 立即失效。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260622_0003'
down_revision: Union[str, None] = '20260622_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('token_version', sa.Integer(),
                      nullable=False, server_default='0')
        )


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('token_version')
