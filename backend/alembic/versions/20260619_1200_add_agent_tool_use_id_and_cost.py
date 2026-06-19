"""add agent_messages.tool_use_id and agent_sessions.cost_usd

Revision ID: a1b2c3d4e5f6
Revises: c63850795dc5
Create Date: 2026-06-19 12:00:00+08:00

Task 4a 架构补列：
- agent_messages.tool_use_id：工具调用 id（tool_use 与 tool_result 配对用），
  替代之前仅靠 seq 顺序关联的脆弱方案。
- agent_sessions.cost_usd：会话累计成本（done 事件写入），让 last_cost_usd
  不再是死代码。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c63850795dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # agent_messages 补 tool_use_id
    op.add_column(
        'agent_messages',
        sa.Column('tool_use_id', sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f('ix_agent_messages_tool_use_id'),
        'agent_messages',
        ['tool_use_id'],
        unique=False,
    )

    # agent_sessions 补 cost_usd
    op.add_column(
        'agent_sessions',
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('agent_sessions', 'cost_usd')
    op.drop_index(
        op.f('ix_agent_messages_tool_use_id'),
        table_name='agent_messages',
    )
    op.drop_column('agent_messages', 'tool_use_id')
