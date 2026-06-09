"""Add is_open field to merchants table

Revision ID: 20260609_0001
Revises: 20260605_0002
Create Date: 2026-06-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260609_0001'
down_revision: Union[str, None] = '20260605_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(connection, table_name, column_name):
    """检查 SQLite 表中是否存在指定列"""
    result = connection.execute(sa.text(f"PRAGMA table_info({table_name})"))
    for row in result:
        if row[1] == column_name:
            return True
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if not column_exists(conn, 'merchants', 'is_open'):
        op.execute(sa.text("ALTER TABLE merchants ADD COLUMN is_open BOOLEAN DEFAULT 1"))
    op.execute(sa.text("UPDATE merchants SET is_open = 1 WHERE is_open IS NULL"))


def downgrade() -> None:
    # SQLite 不支持 DROP COLUMN，此操作适用于 MySQL/PostgreSQL
    try:
        op.drop_column('merchants', 'is_open')
    except Exception:
        pass
