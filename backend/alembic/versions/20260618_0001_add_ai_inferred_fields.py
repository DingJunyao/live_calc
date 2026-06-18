"""add ai_inferred fields to ingredients and recipe_ingredients

Revision ID: 20260618_0001
Revises: 20260616_0001
Create Date: 2026-06-18 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260618_0001'
down_revision: Union[str, None] = '20260616_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column("ai_inferred", sa.Boolean(), nullable=False,
                  server_default=sa.text("0"))
    )
    op.add_column(
        "recipe_ingredients",
        sa.Column("ai_inferred", sa.Boolean(), nullable=False,
                  server_default=sa.text("0"))
    )


def downgrade() -> None:
    op.drop_column("recipe_ingredients", "ai_inferred")
    op.drop_column("ingredients", "ai_inferred")
