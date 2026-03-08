"""add_unit_foreign_keys

Revision ID: b2b4bee6ffa9
Revises: c2c83a3a2304
Create Date: 2026-03-07 20:11:34.031268+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2b4bee6ffa9'
down_revision: Union[str, None] = 'c2c83a3a2304'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 使用 batch 模式以支持 SQLite 约束修改
    with op.batch_alter_table('recipe_ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_recipe_ingredients_unit_id_units',
            'units',
            ['unit_id'], ['id']
        )
        batch_op.drop_column('unit')

    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_unit_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_ingredients_default_unit_id_units',
            'units',
            ['default_unit_id'], ['id']
        )
        batch_op.drop_column('default_unit')

    with op.batch_alter_table('product_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('original_unit_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            'fk_product_records_original_unit_id_units',
            'units',
            ['original_unit_id'], ['id']
        )
        batch_op.drop_column('original_unit')

        batch_op.add_column(sa.Column('standard_unit_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            'fk_product_records_standard_unit_id_units',
            'units',
            ['standard_unit_id'], ['id']
        )
        batch_op.drop_column('standard_unit')


def downgrade() -> None:
    # 使用 batch 模式以支持 SQLite 约束修改
    with op.batch_alter_table('product_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('standard_unit', sa.String(length=20), nullable=False, server_default='g'))
        batch_op.add_column(sa.Column('original_unit', sa.String(length=20), nullable=False))
        batch_op.drop_constraint('fk_product_records_standard_unit_id_units', type_='foreignkey')
        batch_op.drop_column('standard_unit_id')
        batch_op.drop_constraint('fk_product_records_original_unit_id_units', type_='foreignkey')
        batch_op.drop_column('original_unit_id')

    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_unit', sa.String(length=20), nullable=True))
        batch_op.drop_constraint('fk_ingredients_default_unit_id_units', type_='foreignkey')
        batch_op.drop_column('default_unit_id')

    with op.batch_alter_table('recipe_ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit', sa.String(length=20), nullable=True))
        batch_op.drop_constraint('fk_recipe_ingredients_unit_id_units', type_='foreignkey')
        batch_op.drop_column('unit_id')
