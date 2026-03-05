"""fix: 为 ProductIngredientLink 添加完整的审计字段（created_by, updated_by, is_active）

Revision ID: 6ac4335a4eb0
Revises: 32de12f1b4d9
Create Date: 2026-03-05 19:23:23.587605+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ac4335a4eb0'
down_revision: Union[str, None] = '32de12f1b4d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 不支持直接修改表结构，需要重建表
    # 这个迁移在手动执行时已完成，这里仅记录
    op.execute("""
        -- 创建新的 product_ingredient_links 表，包含完整的审计字段
        CREATE TABLE product_ingredient_links_new (
            id INTEGER NOT NULL PRIMARY KEY,
            product_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            created_by INTEGER,
            updated_by INTEGER,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
            FOREIGN KEY(created_by) REFERENCES users(id),
            FOREIGN KEY(updated_by) REFERENCES users(id)
        );

        -- 迁移数据
        INSERT INTO product_ingredient_links_new (id, product_id, ingredient_id, created_at, updated_at, is_active)
        SELECT id, product_id, ingredient_id, created_at,
               COALESCE(updated_at, created_at, CURRENT_TIMESTAMP), 1
        FROM product_ingredient_links;

        -- 删除旧表
        DROP TABLE product_ingredient_links;

        -- 重命名新表
        ALTER TABLE product_ingredient_links_new RENAME TO product_ingredient_links;

        -- 重建索引
        CREATE INDEX ix_product_ingredient_links_id ON product_ingredient_links(id);
    """)


def downgrade() -> None:
    # 回滚到原始结构
    op.execute("""
        -- 创建旧的 product_ingredient_links 表结构
        CREATE TABLE product_ingredient_links_old (
            id INTEGER NOT NULL PRIMARY KEY,
            product_record_id INTEGER,
            ingredient_id INTEGER,
            match_confidence NUMERIC(3, 2),
            match_method VARCHAR(50),
            verified_by_user BOOLEAN,
            verification_notes VARCHAR(500),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            product_id INTEGER NOT NULL,
            FOREIGN KEY(product_record_id) REFERENCES product_records(id),
            FOREIGN KEY(ingredient_id) REFERENCES ingredients(id)
        );

        -- 迁移数据
        INSERT INTO product_ingredient_links_old (id, product_record_id, ingredient_id, created_at, updated_at, product_id)
        SELECT id, product_id, ingredient_id, created_at, updated_at, product_id
        FROM product_ingredient_links;

        -- 删除新表
        DROP TABLE product_ingredient_links;

        -- 重命名旧表
        ALTER TABLE product_ingredient_links_old RENAME TO product_ingredient_links;

        -- 重建索引
        CREATE INDEX ix_product_ingredient_links_id ON product_ingredient_links(id);
    """)
