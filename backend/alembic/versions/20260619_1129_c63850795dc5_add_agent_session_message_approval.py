"""add agent session/message/approval

Revision ID: c63850795dc5
Revises: 20260619_0001
Create Date: 2026-06-19 11:29:47.563225+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c63850795dc5'
down_revision: Union[str, None] = '20260619_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: autogenerate 误判把已有的 import_tasks 表识别为「待删除」，
    # 实际该表与本 Task 无关，已手修移除相关 drop 操作。

    # agent_sessions
    op.create_table('agent_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=32), nullable=True),
        sa.Column('title', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('runner_type', sa.String(length=20), nullable=False),
        sa.Column('claude_session_id', sa.String(length=128), nullable=True),
        sa.Column('initial_prompt', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_sessions_id'), 'agent_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_agent_sessions_task_type'), 'agent_sessions', ['task_type'], unique=False)

    # agent_messages
    op.create_table('agent_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('seq', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=16), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tool_name', sa.String(length=64), nullable=True),
        sa.Column('tool_input', sa.JSON(), nullable=True),
        sa.Column('tool_result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['agent_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_messages_id'), 'agent_messages', ['id'], unique=False)
    op.create_index(op.f('ix_agent_messages_session_id'), 'agent_messages', ['session_id'], unique=False)

    # agent_approvals
    op.create_table('agent_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('sql', sa.Text(), nullable=False),
        sa.Column('danger_reason', sa.String(length=128), nullable=True),
        sa.Column('affected_estimate', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('decided_by', sa.Integer(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['decided_by'], ['users.id']),
        sa.ForeignKeyConstraint(['message_id'], ['agent_messages.id']),
        sa.ForeignKeyConstraint(['session_id'], ['agent_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_approvals_id'), 'agent_approvals', ['id'], unique=False)
    op.create_index(op.f('ix_agent_approvals_session_id'), 'agent_approvals', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agent_approvals_session_id'), table_name='agent_approvals')
    op.drop_index(op.f('ix_agent_approvals_id'), table_name='agent_approvals')
    op.drop_table('agent_approvals')
    op.drop_index(op.f('ix_agent_messages_session_id'), table_name='agent_messages')
    op.drop_index(op.f('ix_agent_messages_id'), table_name='agent_messages')
    op.drop_table('agent_messages')
    op.drop_index(op.f('ix_agent_sessions_task_type'), table_name='agent_sessions')
    op.drop_index(op.f('ix_agent_sessions_id'), table_name='agent_sessions')
    op.drop_table('agent_sessions')
