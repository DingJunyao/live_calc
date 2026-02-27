#!/usr/bin/env python3
"""
初始化审计字段值的脚本
确保现有记录有正确的审计字段值
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import settings
from datetime import datetime

def initialize_audit_fields():
    """初始化审计字段"""
    print("开始初始化审计字段...")

    # 创建数据库引擎
    engine = create_engine(settings.database_url)

    try:
        with engine.connect() as conn:
            # 确保所有记录都有合适的 is_active 值
            tables_to_update = [
                'ingredients',
                'ingredient_categories',
                'ingredient_densities',
                'ingredient_hierarchy',
                'units',
                'unit_conversions',
                'nutrition_data',
                'ingredient_nutrition_mapping'
            ]

            for table in tables_to_update:
                print(f"处理表 {table}...")

                # 对于已存在的记录，如果is_active是NULL，设置为True
                update_is_active = text(f"""
                    UPDATE {table}
                    SET is_active = 1
                    WHERE is_active IS NULL OR is_active = 0
                """)
                conn.execute(update_is_active)

                # 对于已存在的记录，如果created_at是NULL，设置为当前时间
                update_created_at = text(f"""
                    UPDATE {table}
                    SET created_at = CURRENT_TIMESTAMP
                    WHERE created_at IS NULL
                """)
                conn.execute(update_created_at)

                # 对于已存在的记录，设置updated_at为创建时间或当前时间
                update_updated_at = text(f"""
                    UPDATE {table}
                    SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
                    WHERE updated_at IS NULL AND created_at IS NOT NULL
                """)
                conn.execute(update_updated_at)

            conn.commit()
            print("审计字段初始化完成!")

    except Exception as e:
        print(f"初始化审计字段失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    initialize_audit_fields()