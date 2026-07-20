"""User 模型加 avatar/nickname 列

Revision ID: 20260720_user_avatar_nickname
Revises: 20260720_storage_key
Create Date: 2026-07-20

- avatar VARCHAR(500) — storage key（如 avatars/uuid.png），nullable
- nickname VARCHAR(50) — 显示名，nullable，空时前端回退为 username
"""
from alembic import op
import sqlalchemy as sa


revision = "20260720_user_avatar_nickname"
down_revision = "20260720_storage_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("nickname", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "nickname")
    op.drop_column("users", "avatar")
