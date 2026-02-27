#!/usr/bin/env python3
"""
单独为每个表添加updated_at字段
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import settings

def add_updated_at_to_each_table():
    """为每个表单独添加updated_at字段"""
    print("开始为每个表添加updated_at字段...")

    # 创建数据库引擎
    engine = create_engine(settings.database_url)

    # 要处理的表列表
    tables = [
        'ingredient_categories',
        'ingredient_densities',
        'ingredient_hierarchy',
        'units',
        'unit_conversions',
        'nutrition_data',
        'ingredient_nutrition_mapping'
    ]

    try:
        with engine.connect() as conn:
            for table in tables:
                print(f"处理表 {table}...")

                # 尝试添加updated_at列
                try:
                    add_column_sql = text(f"ALTER TABLE {table} ADD COLUMN updated_at DATETIME;")
                    conn.execute(add_column_sql)
                    print(f"  已添加updated_at列到 {table}")
                except Exception as e:
                    print(f"  列可能已存在，跳过: {e}")

                # 尝试更新数据
                try:
                    update_sql = text(f"UPDATE {table} SET updated_at = created_at WHERE updated_at IS NULL AND created_at IS NOT NULL;")
                    conn.execute(update_sql)
                    print(f"  已更新 {table} 中的updated_at数据")
                except Exception as e:
                    print(f"  更新数据时出现问题: {e}")

            conn.commit()
            print("所有表的updated_at字段已添加完成!")

    except Exception as e:
        print(f"添加updated_at字段失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    add_updated_at_to_each_table()