"""add serving_weight to ingredients

Revision ID: 20260615_0001
Revises: 20260614_195120
Create Date: 2026-06-15 10:00:00.000000

为 ingredients 新增 serving_weight + serving_weight_unit_id，
用于"半成品制作菜谱"的成本换算（成品基准量）。
语义：servings 是它的倍数，total_yield = servings × serving_weight(折算为克)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260615_0001'
down_revision: Union[str, None] = '20260614_195120'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 使用 batch 模式以支持 SQLite 约束修改（与 piece_weight 迁移保持一致）
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'serving_weight',
                sa.Numeric(10, 3),
                nullable=True,
                comment='成品基准量（每份/每基准单位多重），用于制作菜谱成本换算'
            )
        )
        batch_op.add_column(
            sa.Column(
                'serving_weight_unit_id',
                sa.Integer(),
                nullable=True,
                comment='成品基准量单位ID'
            )
        )
        batch_op.create_foreign_key(
            'fk_ingredients_serving_weight_unit_id_units',
            'units',
            ['serving_weight_unit_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ingredients_serving_weight_unit_id_units', type_='foreignkey')
        batch_op.drop_column('serving_weight_unit_id')
        batch_op.drop_column('serving_weight')
