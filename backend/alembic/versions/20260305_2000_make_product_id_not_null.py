"""Make product_id not nullable in product_records

Revision ID: make_product_id_not_null
Revises: 32de12f1b4d9
Create Date: 2026-03-05 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'make_product_id_not_null'
down_revision = '32de12f1b4d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 步骤 1: 为没有 product_id 的记录创建临时商品和食材
    connection = op.get_bind()

    # 首先创建临时食材
    connection.execute(sa.text("""
        INSERT INTO ingredients (name, is_imported, created_by, updated_by, is_active, created_at, updated_at)
        SELECT DISTINCT
            pr.product_name,
            1 as is_imported,
            pr.user_id as created_by,
            pr.user_id as updated_by,
            1 as is_active,
            datetime('now') as created_at,
            datetime('now') as updated_at
        FROM product_records pr
        WHERE pr.product_id IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM ingredients i WHERE i.name = pr.product_name AND i.is_active = 1
        )
    """))

    # 然后创建临时商品
    connection.execute(sa.text("""
        INSERT INTO products (name, ingredient_id, created_by, updated_by, is_active, created_at, updated_at)
        SELECT DISTINCT
            pr.product_name,
            i.id as ingredient_id,
            pr.user_id as created_by,
            pr.user_id as updated_by,
            1 as is_active,
            datetime('now') as created_at,
            datetime('now') as updated_at
        FROM product_records pr
        INNER JOIN ingredients i ON i.name = pr.product_name AND i.is_active = 1
        WHERE pr.product_id IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM products p WHERE p.name = pr.product_name AND p.ingredient_id = i.id AND p.is_active = 1
        )
    """))

    # 更新 product_id
    connection.execute(sa.text("""
        UPDATE product_records
        SET product_id = (
            SELECT p.id
            FROM products p
            WHERE p.name = product_records.product_name
            LIMIT 1
        )
        WHERE product_id IS NULL
    """))

    # 步骤 2: 重建表，使 product_id 成为 NOT NULL
    # SQLite 方式：创建新表，复制数据，删除旧表，重命名新表
    with op.batch_alter_table('product_records', recreate='always') as batch_op:
        batch_op.alter_column(
            'product_id',
            existing_type=sa.Integer(),
            nullable=False
        )


def downgrade() -> None:
    # 降级操作
    with op.batch_alter_table('product_records', recreate='always') as batch_op:
        batch_op.alter_column(
            'product_id',
            existing_type=sa.Integer(),
            nullable=True
        )
