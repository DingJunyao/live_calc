"""shared data transform: merchant user_id nullable, recipe is_public, unit is_standard, favorites + price summary

Revision ID: 20260627_0002
Revises: 20260627_0001
Create Date: 2026-06-27 11:00:00+08:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260627_0002'
down_revision: Union[str, None] = '20260627_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merchant.user_id 改 nullable（语义从「拥有者」改为「录入者」，私有归属改由 user_merchant_favorites 表表达）
    with op.batch_alter_table('merchants') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=True)
    # recipe.is_public
    with op.batch_alter_table('recipes') as batch_op:
        batch_op.add_column(sa.Column('is_public', sa.Boolean(),
                                      nullable=False, server_default=sa.text('false')))
    # unit.is_standard（unit_system 已存在，仅新增 is_standard）
    with op.batch_alter_table('units') as batch_op:
        batch_op.add_column(sa.Column('is_standard', sa.Boolean(),
                                      nullable=False, server_default=sa.text('false')))
    # 收藏表
    op.create_table(
        'user_merchant_favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchants.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'merchant_id', name='uq_user_merchant'),
    )
    op.create_index('ix_user_merchant_favorites_user_id', 'user_merchant_favorites', ['user_id'])
    op.create_index('ix_user_merchant_favorites_merchant_id', 'user_merchant_favorites', ['merchant_id'])
    # 价格汇总表
    op.create_table(
        'product_merchant_price_summary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchants.id'), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recent_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('avg_price_30d', sa.Numeric(10, 2), nullable=True),
        sa.Column('min_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('max_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pmp_summary_product', 'product_merchant_price_summary', ['product_id'])
    op.create_index('ix_pmp_summary_merchant', 'product_merchant_price_summary', ['merchant_id'])
    # 迁移：现有「拥有」商家 → 收藏（按引擎语法）
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        op.execute("""
            INSERT OR IGNORE INTO user_merchant_favorites (user_id, merchant_id, created_at)
            SELECT DISTINCT user_id, id, CURRENT_TIMESTAMP FROM merchants WHERE user_id IS NOT NULL
        """)
    elif bind.dialect.name == 'mysql':
        op.execute("""
            INSERT IGNORE INTO user_merchant_favorites (user_id, merchant_id, created_at)
            SELECT DISTINCT user_id, id, NOW() FROM merchants WHERE user_id IS NOT NULL
        """)
    elif bind.dialect.name == 'postgresql':
        op.execute("""
            INSERT INTO user_merchant_favorites (user_id, merchant_id, created_at)
            SELECT DISTINCT user_id, id, NOW() FROM merchants WHERE user_id IS NOT NULL
            ON CONFLICT (user_id, merchant_id) DO NOTHING
        """)


def downgrade() -> None:
    op.drop_index('ix_pmp_summary_merchant', table_name='product_merchant_price_summary')
    op.drop_index('ix_pmp_summary_product', table_name='product_merchant_price_summary')
    op.drop_table('product_merchant_price_summary')
    op.drop_index('ix_user_merchant_favorites_merchant_id', table_name='user_merchant_favorites')
    op.drop_index('ix_user_merchant_favorites_user_id', table_name='user_merchant_favorites')
    op.drop_table('user_merchant_favorites')
    with op.batch_alter_table('units') as batch_op:
        batch_op.drop_column('is_standard')
    with op.batch_alter_table('recipes') as batch_op:
        batch_op.drop_column('is_public')
    with op.batch_alter_table('merchants') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
