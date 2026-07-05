"""add user unit preferences and drop ingredient default_unit_id

Revision ID: 20260705_0001
Revises: 20260704_0001
Create Date: 2026-07-05

users 加 4 列单位偏好（default_energy_unit / default_mass_unit_id /
default_volume_unit_id / default_price_unit_id），并删除 ingredients.default_unit_id
（含外键 + index），改由用户级偏好统一驱动默认单位。
"""
from alembic import op
import sqlalchemy as sa


revision = "20260705_0001"
down_revision = "20260704_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # User 加 4 列单位偏好
    op.add_column('users', sa.Column('default_energy_unit', sa.String(10), nullable=True))
    op.add_column('users', sa.Column('default_mass_unit_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('default_volume_unit_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('default_price_unit_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_default_mass_unit', 'users', 'units',
                          ['default_mass_unit_id'], ['id'])
    op.create_foreign_key('fk_users_default_volume_unit', 'users', 'units',
                          ['default_volume_unit_id'], ['id'])
    op.create_foreign_key('fk_users_default_price_unit', 'users', 'units',
                          ['default_price_unit_id'], ['id'])

    # Ingredient 删 default_unit_id（SQLite 需表重建，batch_alter 跨引擎安全）
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.drop_column('default_unit_id')


def downgrade() -> None:
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.add_column(sa.Column('default_unit_id', sa.Integer(),
                                      sa.ForeignKey('units.id'), nullable=True))
    op.drop_constraint('fk_users_default_price_unit', 'users', type_='foreignkey')
    op.drop_constraint('fk_users_default_volume_unit', 'users', type_='foreignkey')
    op.drop_constraint('fk_users_default_mass_unit', 'users', type_='foreignkey')
    op.drop_column('users', 'default_price_unit_id')
    op.drop_column('users', 'default_volume_unit_id')
    op.drop_column('users', 'default_mass_unit_id')
    op.drop_column('users', 'default_energy_unit')
