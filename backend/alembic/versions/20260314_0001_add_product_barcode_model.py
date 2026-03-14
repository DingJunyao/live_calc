"""Add ProductBarcode model and update Product model

Revision ID: 20260314_0001
Revises: 20260312_0003
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite, postgresql, mysql

# revision identifiers, used by Alembic.
revision: str = '20260314_0001'
down_revision: Union[str, None] = 'add_custom_nutrition'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 product_barcodes 表
    op.create_table(
        'product_barcodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('barcode', sa.String(length=50), nullable=False),
        sa.Column('barcode_type', sa.String(length=20), nullable=True, server_default='internal'),
        sa.Column('is_primary', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('barcode')
    )

    # 创建索引
    op.create_index(op.f('ix_product_barcodes_id'), 'product_barcodes', ['id'], unique=False)
    op.create_index(op.f('ix_product_barcodes_product_id'), 'product_barcodes', ['product_id'], unique=False)
    op.create_index(op.f('ix_product_barcodes_barcode'), 'product_barcodes', ['barcode'], unique=True)

    # 迁移现有条码数据到新表
    op.execute("""
        INSERT INTO product_barcodes (product_id, barcode, barcode_type, is_primary, is_active, created_at, updated_at)
        SELECT id, barcode, 'internal', 1, 1, created_at, updated_at
        FROM products
        WHERE barcode IS NOT NULL
    """)

    # 移除 products 表的 barcode 字段（SQLite 不支持直接删除列，需要重建表）
    if op.get_context().dialect.name == 'sqlite':
        # SQLite 需要重建表
        op.execute("""
            CREATE TABLE products_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                brand VARCHAR(100),
                image_url VARCHAR(500),
                ingredient_id INTEGER NOT NULL,
                tags VARCHAR(500),
                custom_nutrition_data JSON,
                custom_nutrition_source VARCHAR(50) DEFAULT 'custom',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
                FOREIGN KEY(created_by) REFERENCES users(id),
                FOREIGN KEY(updated_by) REFERENCES users(id)
            )
        """)

        op.execute("""
            INSERT INTO products_new (id, name, brand, image_url, ingredient_id, tags,
                                      custom_nutrition_data, custom_nutrition_source,
                                      created_at, updated_at, created_by, updated_by, is_active)
            SELECT id, name, brand, image_url, ingredient_id, tags,
                   custom_nutrition_data, custom_nutrition_source,
                   created_at, updated_at, created_by, updated_by, is_active
            FROM products
        """)

        op.execute('DROP TABLE products')
        op.execute('ALTER TABLE products_new RENAME TO products')

        # 重建索引
        op.create_index(op.f('ix_products_id'), 'products', ['id'])
        op.create_index(op.f('ix_products_name'), 'products', ['name'])
        op.create_index(op.f('ix_products_ingredient_id'), 'products', ['ingredient_id'])

    else:
        # PostgreSQL/MySQL 可以直接删除列
        op.drop_column('products', 'barcode')


def downgrade() -> None:
    # 恢复 products 表的 barcode 字段
    if op.get_context().dialect.name == 'sqlite':
        # SQLite 需要重建表
        op.execute("""
            CREATE TABLE products_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                brand VARCHAR(100),
                barcode VARCHAR(50) UNIQUE,
                image_url VARCHAR(500),
                ingredient_id INTEGER NOT NULL,
                tags VARCHAR(500),
                custom_nutrition_data JSON,
                custom_nutrition_source VARCHAR(50) DEFAULT 'custom',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
                FOREIGN KEY(created_by) REFERENCES users(id),
                FOREIGN KEY(updated_by) REFERENCES users(id)
            )
        """)

        op.execute("""
            INSERT INTO products_new (id, name, brand, barcode, image_url, ingredient_id, tags,
                                      custom_nutrition_data, custom_nutrition_source,
                                      created_at, updated_at, created_by, updated_by, is_active)
            SELECT p.id, p.name, p.brand, pb.barcode, p.image_url, p.ingredient_id, p.tags,
                   p.custom_nutrition_data, p.custom_nutrition_source,
                   p.created_at, p.updated_at, p.created_by, p.updated_by, p.is_active
            FROM products p
            LEFT JOIN product_barcodes pb ON p.id = pb.product_id AND pb.is_primary = 1
        """)

        op.execute('DROP TABLE products')
        op.execute('ALTER TABLE products_new RENAME TO products')

        # 重建索引
        op.create_index(op.f('ix_products_id'), 'products', ['id'])
        op.create_index(op.f('ix_products_name'), 'products', ['name'])
        op.create_index(op.f('ix_products_ingredient_id'), 'products', ['ingredient_id'])

    else:
        # PostgreSQL/MySQL 可以直接添加列
        op.add_column('products', sa.Column('barcode', sa.String(length=50), nullable=True))
        op.create_unique_constraint('uq_products_barcode', 'products', ['barcode'])

        # 从 product_barcodes 迁移主条码回 products 表
        op.execute("""
            UPDATE products p
            SET barcode = pb.barcode
            FROM product_barcodes pb
            WHERE p.id = pb.product_id AND pb.is_primary = 1
        """)

    # 删除 product_barcodes 表
    op.drop_index(op.f('ix_product_barcodes_barcode'), table_name='product_barcodes')
    op.drop_index(op.f('ix_product_barcodes_product_id'), table_name='product_barcodes')
    op.drop_index(op.f('ix_product_barcodes_id'), table_name='product_barcodes')
    op.drop_table('product_barcodes')
