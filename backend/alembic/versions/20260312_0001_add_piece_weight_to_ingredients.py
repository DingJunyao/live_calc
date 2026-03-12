"""add_piece_weight_to_ingredients

Revision ID: a1b2c3d4e5f6
Revises: b2b4bee6ffa9
Create Date: 2026-03-12 00:00:00.000000+08:00

添加 piece_weight 和 piece_weight_unit_id 字段到 ingredients 表，
用于支持计数单位（如"个"、"只"）到质量单位的转换。
例如：1个鸡蛋=50g，1个土豆=150g
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b2b4bee6ffa9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 使用 batch 模式以支持 SQLite 约束修改
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'piece_weight',
                sa.Numeric(10, 3),
                nullable=True,
                comment='每个单位的标准重量（如1个鸡蛋=50g）'
            )
        )
        batch_op.add_column(
            sa.Column(
                'piece_weight_unit_id',
                sa.Integer(),
                nullable=True,
                comment='重量单位ID（如3=g）'
            )
        )
        batch_op.create_foreign_key(
            'fk_ingredients_piece_weight_unit_id_units',
            'units',
            ['piece_weight_unit_id'], ['id']
        )


def downgrade() -> None:
    # 使用 batch 模式以支持 SQLite 约束修改
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ingredients_piece_weight_unit_id_units', type_='foreignkey')
        batch_op.drop_column('piece_weight_unit_id')
        batch_op.drop_column('piece_weight')
