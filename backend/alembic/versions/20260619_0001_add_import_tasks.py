"""add import_tasks table

Revision ID: 20260619_0001
Revises: 20260618_0001
Create Date: 2026-06-19 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '20260619_0001'
down_revision: Union[str, None] = '20260618_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("progress", sa.JSON(), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_tasks_id"), "import_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_import_tasks_task_type"), "import_tasks", ["task_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_import_tasks_task_type"), table_name="import_tasks")
    op.drop_index(op.f("ix_import_tasks_id"), table_name="import_tasks")
    op.drop_table("import_tasks")
