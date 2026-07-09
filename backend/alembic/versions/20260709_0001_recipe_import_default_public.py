"""recipe import default public

Revision ID: 20260709_0001
Revises: 20260707_0001
Create Date: 2026-07-09

将导入来源（source 非空且非 'custom'）的菜谱 is_public 置 true，
配合「公共/已发布」判断统一改为只看 is_public（方案 A：菜谱发布默认私有）。
纯数据 UPDATE，无表结构变更。
"""
from alembic import op
import sqlalchemy as sa


revision = "20260709_0001"
down_revision = "20260707_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE recipes SET is_public = true "
            "WHERE source IS NOT NULL AND source <> 'custom' AND is_public = false"
        )
    )


def downgrade() -> None:
    # 回滚有损：无法区分「迁移前就是 public」与「本次置 public」的导入菜谱，
    # 故不自动回滚（noop），如确需回滚请手工处理。
    pass
