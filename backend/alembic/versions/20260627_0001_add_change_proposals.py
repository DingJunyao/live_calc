"""add change_proposals table

Revision ID: 20260627_0001
Revises: 20260626_0003
Create Date: 2026-06-27 10:00:00+08:00

通用变更提议表：治理共享数据的写入（普通用户提交 → 审核流转）。
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260627_0001'
down_revision: Union[str, None] = '20260626_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'change_proposals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=True),
        sa.Column('revert_payload', sa.JSON(), nullable=True),
        sa.Column('review_policy', sa.String(16), nullable=False, server_default='manual'),
        sa.Column('risk_level', sa.String(8), nullable=False, server_default='mid'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('proposer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('revertable_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reverted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_change_proposals_entity_type', 'change_proposals', ['entity_type'])
    op.create_index('ix_change_proposals_entity_id', 'change_proposals', ['entity_id'])
    op.create_index('ix_change_proposals_status', 'change_proposals', ['status'])
    op.create_index('ix_change_proposals_proposer_id', 'change_proposals', ['proposer_id'])


def downgrade() -> None:
    op.drop_index('ix_change_proposals_proposer_id', table_name='change_proposals')
    op.drop_index('ix_change_proposals_status', table_name='change_proposals')
    op.drop_index('ix_change_proposals_entity_id', table_name='change_proposals')
    op.drop_index('ix_change_proposals_entity_type', table_name='change_proposals')
    op.drop_table('change_proposals')
