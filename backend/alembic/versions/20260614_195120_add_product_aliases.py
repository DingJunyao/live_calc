"""add product aliases column

Revision ID: 20260614_195120
Revises: (none - initial migration)
Create Date: 2026-06-14 19:51:20.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260614_195120"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加 aliases 列到 products 表"""
    # SQLite 支持 ALTER TABLE ADD COLUMN（但只能追加，不能加约束）
    # JSON 类型在 SQLite 中存储为 TEXT
    op.add_column("products", sa.Column("aliases", sa.JSON(), nullable=True))


def downgrade() -> None:
    """移除 aliases 列"""
    # SQLite 不支持 DROP COLUMN（SQLite < 3.35.0），但默认使用 >= 3.35.0
    # 对于旧版 SQLite，需要重建表，这里使用标准语法
    op.drop_column("products", "aliases")
