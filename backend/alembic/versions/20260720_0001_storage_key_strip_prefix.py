"""图片路径剥前缀成 key

Revision ID: 20260720_storage_key
Revises: 20260719_0001
Create Date: 2026-07-20

DB 只存 key（relative path），不再存带前缀的完整路径。
- recipes.images（JSON 数组 TEXT 列）：整体 REPLACE 剥 /static/images/
- products.image_url（String）：只改被影响的行，外链 http(s):// 不动
纯数据 UPDATE，无表结构变更。
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_storage_key"
down_revision = "20260719_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # recipes.images 是 JSON 数组存为 TEXT，REPLACE 是纯文本替换
    # "/static/images/recipes/xxx.jpg" → "recipes/xxx.jpg"
    op.execute(
        sa.text(
            "UPDATE recipes SET images = REPLACE(images, '/static/images/', '')"
        )
    )
    # products.image_url 只处理带前缀的本地路径，外链不动
    op.execute(
        sa.text(
            "UPDATE products SET image_url = REPLACE(image_url, '/static/images/', '') "
            "WHERE image_url LIKE '/static/images/%'"
        )
    )


def downgrade() -> None:
    # recipes：把 JSON 中的 "recipes/ 前缀恢复为 "/static/images/recipes/
    op.execute(
        sa.text(
            "UPDATE recipes SET images = "
            "REPLACE(images, '\"recipes/', '\"/static/images/recipes/')"
        )
    )
    # products：对非外链、非绝对路径的 key 重新加上 /static/images/ 前缀
    op.execute(
        sa.text(
            "UPDATE products SET image_url = "
            "'/static/images/' || image_url "
            "WHERE image_url NOT LIKE 'http%' AND image_url NOT LIKE '/%'"
        )
    )
