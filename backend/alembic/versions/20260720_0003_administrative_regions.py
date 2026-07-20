"""Create administrative_regions table + add region_id to users

Revision ID: 20260720_0003
Revises: 20260720_user_avatar_nickname
Create Date: 2026-07-20

- create administrative_regions table
- add region_id to users
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_0003"
down_revision = "20260720_user_avatar_nickname"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建行政区划表
    op.create_table(
        "administrative_regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("iso_country", sa.String(length=2), nullable=True),
        sa.Column("path", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_administrative_regions_code",
        "administrative_regions",
        ["code"],
        unique=True,
    )
    op.create_index(
        "ix_administrative_regions_parent_id",
        "administrative_regions",
        ["parent_id"],
    )
    op.create_index(
        "ix_administrative_regions_level",
        "administrative_regions",
        ["level"],
    )
    op.create_foreign_key(
        "fk_administrative_regions_parent",
        "administrative_regions",
        "administrative_regions",
        ["parent_id"],
        ["id"],
    )

    # 给 users 表加 region_id
    op.add_column(
        "users",
        sa.Column("region_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_region_id",
        "users",
        "administrative_regions",
        ["region_id"],
        ["id"],
    )


def downgrade() -> None:
    # 先删 users 的外键和列
    op.drop_constraint("fk_users_region_id", "users", type_="foreignkey")
    op.drop_column("users", "region_id")

    # 再删 administrative_regions 表
    op.drop_constraint(
        "fk_administrative_regions_parent",
        "administrative_regions",
        type_="foreignkey",
    )
    op.drop_index("ix_administrative_regions_level", table_name="administrative_regions")
    op.drop_index("ix_administrative_regions_parent_id", table_name="administrative_regions")
    op.drop_index("ix_administrative_regions_code", table_name="administrative_regions")
    op.drop_table("administrative_regions")
