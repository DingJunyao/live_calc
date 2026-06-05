"""add source column to entity_unit_overrides

Revision ID: 20260605_0001
Revises: fa24d2d1491a
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260605_0001'
down_revision: Union[str, None] = 'fa24d2d1491a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否已存在"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("PRAGMA table_info(:table)"),
        {"table": table_name}
    )
    columns = [row[1] for row in result]
    return column_name in columns


def upgrade() -> None:
    if not _column_exists('entity_unit_overrides', 'source'):
        op.add_column(
            'entity_unit_overrides',
            sa.Column('source', sa.String(20), server_default='manual', nullable=True)
        )


def downgrade() -> None:
    # SQLite 不支持 DROP COLUMN（3.35.0 之前）
    # 如需回滚，请手动重建表
    pass
