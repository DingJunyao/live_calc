"""add external_session_id and drop claude_session_id

Revision ID: 20260806_0001
Revises: 20260723_0001
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

revision = "20260806_0001"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_sessions", sa.Column("external_session_id", sa.String(128), nullable=True))
    op.execute("UPDATE agent_sessions SET external_session_id = claude_session_id")
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.drop_column("claude_session_id")


def downgrade() -> None:
    op.add_column("agent_sessions", sa.Column("claude_session_id", sa.String(128), nullable=True))
    op.execute("UPDATE agent_sessions SET claude_session_id = external_session_id")
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.drop_column("external_session_id")
