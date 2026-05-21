"""add_unit_system_and_entity_tables

Revision ID: fa24d2d1491a
Revises: 20260320_0001
Create Date: 2026-05-21 18:32:14.444750+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa24d2d1491a'
down_revision: Union[str, None] = '20260320_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """检查表是否已存在"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name}
    )
    return result.fetchone() is not None


def _column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否已存在"""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(f"PRAGMA table_info({table_name})")
    )
    return any(row[1] == column_name for row in result.fetchall())


def upgrade() -> None:
    # 1. units 表新增 unit_system 和 default_estimate 列（幂等）
    if not _column_exists('units', 'unit_system'):
        op.add_column('units', sa.Column('unit_system', sa.String(length=20), nullable=True))
    if not _column_exists('units', 'default_estimate'):
        op.add_column('units', sa.Column('default_estimate', sa.Numeric(precision=10, scale=3), nullable=True))

    # 2. 数据迁移：设置现有单位的 unit_system
    op.execute("UPDATE units SET unit_system = 'metric' WHERE abbreviation IN ('g', 'kg', 'mg', 'L', 'ml', 'mL', 'm', 'cm', 'mm') AND (unit_system IS NULL OR unit_system = '')")
    op.execute("UPDATE units SET unit_system = 'market' WHERE abbreviation IN ('斤', '两', '钱', '杯', '汤匙', '茶匙') AND (unit_system IS NULL OR unit_system = '')")
    op.execute("UPDATE units SET unit_system = 'imperial' WHERE abbreviation IN ('lb', 'oz', 'cup', 'fl oz', 'ft', 'in') AND (unit_system IS NULL OR unit_system = '')")
    op.execute("UPDATE units SET unit_system = 'count' WHERE unit_type = 'count' AND (unit_system IS NULL OR unit_system = '')")

    # 3. 创建 entity_unit_overrides 表（幂等）
    if not _table_exists('entity_unit_overrides'):
        op.create_table(
            'entity_unit_overrides',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('entity_type', sa.String(length=20), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('unit_name', sa.String(length=50), nullable=False),
            sa.Column('base_unit_id', sa.Integer(), nullable=True),
            sa.Column('conversion_factor', sa.Numeric(precision=15, scale=10), nullable=True),
            sa.Column('weight_per_unit', sa.Numeric(precision=10, scale=3), nullable=True),
            sa.Column('weight_unit_id', sa.Integer(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.ForeignKeyConstraint(['base_unit_id'], ['units.id']),
            sa.ForeignKeyConstraint(['weight_unit_id'], ['units.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('entity_type', 'entity_id', 'unit_name', name='uq_entity_unit'),
        )
        op.create_index('ix_entity_unit_overrides_id', 'entity_unit_overrides', ['id'], unique=False)

    # 4. 创建 entity_densities 表（幂等）
    if not _table_exists('entity_densities'):
        op.create_table(
            'entity_densities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('entity_type', sa.String(length=20), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('density', sa.Numeric(precision=10, scale=6), nullable=False),
            sa.Column('temperature', sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column('condition', sa.String(length=100), nullable=True),
            sa.Column('source', sa.String(length=200), nullable=True),
            sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('entity_type', 'entity_id', 'condition', name='uq_entity_density'),
        )
        op.create_index('ix_entity_densities_id', 'entity_densities', ['id'], unique=False)


def downgrade() -> None:
    # 1. 删除 entity_densities 表
    op.drop_index('ix_entity_densities_id', table_name='entity_densities')
    op.drop_table('entity_densities')

    # 2. 删除 entity_unit_overrides 表
    op.drop_index('ix_entity_unit_overrides_id', table_name='entity_unit_overrides')
    op.drop_table('entity_unit_overrides')

    # 3. 删除 units 表新增的列
    op.drop_column('units', 'default_estimate')
    op.drop_column('units', 'unit_system')
