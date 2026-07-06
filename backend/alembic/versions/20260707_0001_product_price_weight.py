"""商品价格权重 + 用户覆盖表

Revision ID: 20260707_0001
Revises: 20260705_0001
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa


revision = "20260707_0001"
down_revision = "20260705_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # products 加全局权重列（三库通用 ADD COLUMN；回填默认 50）
    op.add_column(
        "products",
        sa.Column("price_weight", sa.Integer(), nullable=False, server_default="50"),
    )
    # CHECK 约束（三库均支持；MySQL 8.0+ 支持 inline CHECK）
    op.create_check_constraint(
        "ck_products_price_weight_range",
        "products",
        "price_weight BETWEEN 0 AND 100",
    )

    op.create_table(
        "user_product_weight_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("created_by", sa.Integer()),
        sa.Column("updated_by", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name="ck_upwo_weight_range"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_user_product_weight"),
    )
    op.create_index("ix_upwo_user_active", "user_product_weight_overrides", ["user_id", "is_active"])
    op.create_index("ix_user_product_weight_overrides_product_id", "user_product_weight_overrides", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_user_product_weight_overrides_product_id", table_name="user_product_weight_overrides")
    op.drop_index("ix_upwo_user_active", table_name="user_product_weight_overrides")
    op.drop_table("user_product_weight_overrides")
    op.drop_constraint("ck_products_price_weight_range", "products", type_="check")
    op.drop_column("products", "price_weight")
