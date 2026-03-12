"""add fields for ingredient merge functionality

Revision ID: 20260312_0002
Revises: 20260312_0001
Create Date: 2026-03-12 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '20260312_add_fields_for_ingredient_merge_functionality'
down_revision = '7408e388'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 创建ingredient_hierarchies表，用于层级关系管理
    op.create_table('ingredient_hierarchies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=False),
        sa.Column('child_id', sa.Integer(), nullable=False),
        sa.Column('relation_type', sa.String(20), nullable=False),
        sa.Column('strength', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['ingredients.id'], ),
        sa.ForeignKeyConstraint(['child_id'], ['ingredients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 为ingredient_hierarchies表添加索引
    op.create_index('ix_ingredient_hierarchies_parent_id', 'ingredient_hierarchies', ['parent_id'])
    op.create_index('ix_ingredient_hierarchies_child_id', 'ingredient_hierarchies', ['child_id'])
    op.create_index('ix_ingredient_hierarchies_relation_type', 'ingredient_hierarchies', ['relation_type'])

    # 2. 为ingredients表添加合并相关的字段
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_merged', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('merged_into_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_ingredients_merged_into_id', 'ingredients', 'ingredients', ['merged_into_id'], ['id'])
        batch_op.create_index('ix_ingredients_is_merged', ['is_merged'])
        batch_op.create_index('ix_ingredients_merged_into_id', ['merged_into_id'])

    # 3. 创建ingredient_merge_records表，记录合并历史
    op.create_table('ingredient_merge_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_ingredient_id', sa.Integer(), nullable=False),
        sa.Column('target_ingredient_id', sa.Integer(), nullable=False),
        sa.Column('merged_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['merged_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['source_ingredient_id'], ['ingredients.id'], ),
        sa.ForeignKeyConstraint(['target_ingredient_id'], ['ingredients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. 为新表添加索引
    op.create_index('ix_ingredient_merge_records_source_ingredient_id', 'ingredient_merge_records', ['source_ingredient_id'])
    op.create_index('ix_ingredient_merge_records_target_ingredient_id', 'ingredient_merge_records', ['target_ingredient_id'])
    op.create_index('ix_ingredient_merge_records_merged_by_user_id', 'ingredient_merge_records', ['merged_by_user_id'])


def downgrade():
    # 1. 删除合并记录表
    op.drop_table('ingredient_merge_records')

    # 2. 删除ingredients表的合并相关字段
    with op.batch_alter_table('ingredients', schema=None) as batch_op:
        # 删除外键约束 - 可能有不同的名称，所以我们捕获可能的错误
        try:
            batch_op.drop_constraint('fk_ingredients_merged_into_id', type_='foreignkey')
        except:
            # 尝试其他可能的外键名称
            try:
                batch_op.drop_constraint('ingredients_merged_into_id_fkey', type_='foreignkey')
            except:
                # 如果找不到确切名称，使用通用方法
                pass
        batch_op.drop_index('ix_ingredients_merged_into_id')
        batch_op.drop_index('ix_ingredients_is_merged')
        batch_op.drop_column('merged_into_id')
        batch_op.drop_column('is_merged')

    # 3. 删除层级关系表
    op.drop_index('ix_ingredient_hierarchies_relation_type', table_name='ingredient_hierarchies')
    op.drop_index('ix_ingredient_hierarchies_child_id', table_name='ingredient_hierarchies')
    op.drop_index('ix_ingredient_hierarchies_parent_id', table_name='ingredient_hierarchies')
    op.drop_table('ingredient_hierarchies')