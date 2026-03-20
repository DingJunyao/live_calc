"""Add audit fields to all tables and create operation_logs table

Revision ID: 20260320_0001
Revises: 20260318_0001
Create Date: 2026-03-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260320_0001'
down_revision = '20260318_0001'
branch_labels = None
depends_on = None


def table_exists(connection, table_name):
    """检查表是否存在"""
    result = connection.execute(sa.text(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    ))
    return result.fetchone() is not None


def column_exists(connection, table_name, column_name):
    """检查列是否存在"""
    result = connection.execute(sa.text(f"PRAGMA table_info({table_name})"))
    for row in result:
        if row[1] == column_name:
            return True
    return False


def add_column_if_not_exists(connection, table_name, column_name, column_def):
    """添加列（如果不存在）"""
    if not column_exists(connection, table_name, column_name):
        connection.execute(sa.text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}'))


def upgrade() -> None:
    conn = op.get_bind()

    # 1. 创建操作日志表（如果不存在）
    if not table_exists(conn, 'operation_logs'):
        op.create_table(
            'operation_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('action', sa.String(50), nullable=False),
            sa.Column('table_name', sa.String(100), nullable=False),
            sa.Column('record_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('old_data', sa.JSON(), nullable=True),
            sa.Column('new_data', sa.JSON(), nullable=True),
            sa.Column('changed_fields', sa.JSON(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_operation_logs_id', 'operation_logs', ['id'])
        op.create_index('ix_operation_logs_action', 'operation_logs', ['action'])
        op.create_index('ix_operation_logs_table_name', 'operation_logs', ['table_name'])
        op.create_index('ix_operation_logs_record_id', 'operation_logs', ['record_id'])
        op.create_index('ix_operation_logs_user_id', 'operation_logs', ['user_id'])
        op.create_index('ix_operation_logs_created_at', 'operation_logs', ['created_at'])

    # 2. 给缺失审计字段的表添加字段
    # users 表
    add_column_if_not_exists(conn, 'users', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'users', 'updated_by', 'INTEGER')

    # nutrition_data 表
    add_column_if_not_exists(conn, 'nutrition_data', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'nutrition_data', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'nutrition_data', 'is_active', 'BOOLEAN DEFAULT 1')

    # nrv_standards 表
    add_column_if_not_exists(conn, 'nrv_standards', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'nrv_standards', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'nrv_standards', 'is_active', 'BOOLEAN DEFAULT 1')

    # merchants 表
    add_column_if_not_exists(conn, 'merchants', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'merchants', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'merchants', 'is_active', 'BOOLEAN DEFAULT 1')

    # favorite_merchants 表
    add_column_if_not_exists(conn, 'favorite_merchants', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'favorite_merchants', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'favorite_merchants', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'favorite_merchants', 'is_active', 'BOOLEAN DEFAULT 1')

    # ai_ingredient_matches 表
    add_column_if_not_exists(conn, 'ai_ingredient_matches', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'ai_ingredient_matches', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'ai_ingredient_matches', 'is_active', 'BOOLEAN DEFAULT 1')

    # nutrition_edit_history 表
    add_column_if_not_exists(conn, 'nutrition_edit_history', 'created_at', 'DATETIME')
    add_column_if_not_exists(conn, 'nutrition_edit_history', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'nutrition_edit_history', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'nutrition_edit_history', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'nutrition_edit_history', 'is_active', 'BOOLEAN')

    # expenses 表
    add_column_if_not_exists(conn, 'expenses', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'expenses', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'expenses', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'expenses', 'is_active', 'BOOLEAN')

    # invite_codes 表
    add_column_if_not_exists(conn, 'invite_codes', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'invite_codes', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'invite_codes', 'is_active', 'BOOLEAN')

    # product_records 表 - SQLite 不支持 DEFAULT CURRENT_TIMESTAMP
    add_column_if_not_exists(conn, 'product_records', 'created_at', 'DATETIME')
    add_column_if_not_exists(conn, 'product_records', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'product_records', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'product_records', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'product_records', 'is_active', 'BOOLEAN')

    # recipe_ingredients 表
    add_column_if_not_exists(conn, 'recipe_ingredients', 'created_at', 'DATETIME')
    add_column_if_not_exists(conn, 'recipe_ingredients', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'recipe_ingredients', 'updated_at', 'DATETIME')
    add_column_if_not_exists(conn, 'recipe_ingredients', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'recipe_ingredients', 'is_active', 'BOOLEAN')

    # region_unit_settings 表
    add_column_if_not_exists(conn, 'region_unit_settings', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'region_unit_settings', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'region_unit_settings', 'is_active', 'BOOLEAN DEFAULT 1')

    # user_unit_preferences 表
    add_column_if_not_exists(conn, 'user_unit_preferences', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'user_unit_preferences', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'user_unit_preferences', 'is_active', 'BOOLEAN DEFAULT 1')

    # map_configurations 表
    add_column_if_not_exists(conn, 'map_configurations', 'created_by', 'INTEGER')
    add_column_if_not_exists(conn, 'map_configurations', 'updated_by', 'INTEGER')
    add_column_if_not_exists(conn, 'map_configurations', 'is_active', 'BOOLEAN DEFAULT 1')

    # 更新 is_active 默认值
    conn.execute(sa.text("UPDATE nutrition_data SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE nrv_standards SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE merchants SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE favorite_merchants SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE ai_ingredient_matches SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE nutrition_edit_history SET is_active = 1, created_at = CURRENT_TIMESTAMP WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE expenses SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE invite_codes SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE product_records SET is_active = 1, created_at = CURRENT_TIMESTAMP WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE recipe_ingredients SET is_active = 1, created_at = CURRENT_TIMESTAMP WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE region_unit_settings SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE user_unit_preferences SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE map_configurations SET is_active = 1 WHERE is_active IS NULL"))


def downgrade() -> None:
    # 删除添加的字段
    op.drop_column('map_configurations', 'is_active')
    op.drop_column('map_configurations', 'updated_by')
    op.drop_column('map_configurations', 'created_by')

    op.drop_column('user_unit_preferences', 'is_active')
    op.drop_column('user_unit_preferences', 'updated_by')
    op.drop_column('user_unit_preferences', 'created_by')

    op.drop_column('region_unit_settings', 'is_active')
    op.drop_column('region_unit_settings', 'updated_by')
    op.drop_column('region_unit_settings', 'created_by')

    op.drop_column('recipe_ingredients', 'is_active')
    op.drop_column('recipe_ingredients', 'updated_by')
    op.drop_column('recipe_ingredients', 'updated_at')
    op.drop_column('recipe_ingredients', 'created_by')
    op.drop_column('recipe_ingredients', 'created_at')

    op.drop_column('product_records', 'is_active')
    op.drop_column('product_records', 'updated_by')
    op.drop_column('product_records', 'updated_at')
    op.drop_column('product_records', 'created_by')
    op.drop_column('product_records', 'created_at')

    op.drop_column('invite_codes', 'is_active')
    op.drop_column('invite_codes', 'updated_by')
    op.drop_column('invite_codes', 'updated_at')

    op.drop_column('expenses', 'is_active')
    op.drop_column('expenses', 'updated_by')
    op.drop_column('expenses', 'updated_at')
    op.drop_column('expenses', 'created_by')

    op.drop_column('nutrition_edit_history', 'is_active')
    op.drop_column('nutrition_edit_history', 'updated_by')
    op.drop_column('nutrition_edit_history', 'updated_at')
    op.drop_column('nutrition_edit_history', 'created_by')
    op.drop_column('nutrition_edit_history', 'created_at')

    op.drop_column('ai_ingredient_matches', 'is_active')
    op.drop_column('ai_ingredient_matches', 'updated_by')
    op.drop_column('ai_ingredient_matches', 'updated_at')

    op.drop_column('favorite_merchants', 'is_active')
    op.drop_column('favorite_merchants', 'updated_by')
    op.drop_column('favorite_merchants', 'updated_at')
    op.drop_column('favorite_merchants', 'created_by')

    op.drop_column('merchants', 'is_active')
    op.drop_column('merchants', 'updated_by')
    op.drop_column('merchants', 'created_by')

    op.drop_column('nrv_standards', 'is_active')
    op.drop_column('nrv_standards', 'updated_by')
    op.drop_column('nrv_standards', 'created_by')

    op.drop_column('nutrition_data', 'is_active')
    op.drop_column('nutrition_data', 'updated_by')
    op.drop_column('nutrition_data', 'created_by')

    op.drop_column('users', 'updated_by')
    op.drop_column('users', 'created_by')

    # 删除操作日志表
    op.drop_index('ix_operation_logs_created_at', 'operation_logs')
    op.drop_index('ix_operation_logs_user_id', 'operation_logs')
    op.drop_index('ix_operation_logs_record_id', 'operation_logs')
    op.drop_index('ix_operation_logs_table_name', 'operation_logs')
    op.drop_index('ix_operation_logs_action', 'operation_logs')
    op.drop_index('ix_operation_logs_id', 'operation_logs')
    op.drop_table('operation_logs')