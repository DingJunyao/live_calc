"""unify all ingredient default units to jin (斤)

Revision ID: 20260605_0002
Revises: 20260605_0001
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260605_0002'
down_revision: Union[str, None] = '20260605_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 将所有食材的默认单位统一设为斤
    op.execute("""
        UPDATE ingredients
        SET default_unit_id = (SELECT id FROM units WHERE abbreviation = '斤')
        WHERE default_unit_id IS NOT NULL
          AND default_unit_id != (SELECT id FROM units WHERE abbreviation = '斤')
    """)


def downgrade() -> None:
    # 无法回滚：我们不知道每个食材原来的默认单位是什么
    pass
