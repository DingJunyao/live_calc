"""
迁移脚本：将旧的aliases字段数据迁移到新的name_variants字段
"""

import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.nutrition import Ingredient


def migrate_aliases_to_name_variants():
    db = SessionLocal()

    try:
        # 查询所有具有aliases数据的食材
        ingredients = db.query(Ingredient).all()

        migrated_count = 0
        for ingredient in ingredients:
            # 检查是否已经有name_variants数据
            if ingredient.name_variants is not None:
                continue

            # 如果有旧的aliases数据，则迁移到新的name_variants格式
            if hasattr(ingredient, 'aliases') and ingredient.aliases is not None:
                # 这里的aliases可能是一个JSON字符串或列表
                if isinstance(ingredient.aliases, str):
                    try:
                        # 尝试解析JSON字符串
                        aliases_data = json.loads(ingredient.aliases)
                        if isinstance(aliases_data, list):
                            ingredient.name_variants = {"aliases": aliases_data}
                        else:
                            # 如果不是列表，则可能已经是某种结构，直接使用
                            ingredient.name_variants = {"aliases": [aliases_data] if aliases_data else []}
                    except json.JSONDecodeError:
                        # 如果不是有效的JSON，则将原始字符串作为别名
                        ingredient.name_variants = {"aliases": [ingredient.aliases] if ingredient.aliases else []}
                elif isinstance(ingredient.aliases, list):
                    # 如果aliases已经是列表
                    ingredient.name_variants = {"aliases": ingredient.aliases}
                else:
                    # 其他情况，转换为列表
                    ingredient.name_variants = {"aliases": [ingredient.aliases] if ingredient.aliases else []}

                migrated_count += 1
                print(f"Migrated ingredient: {ingredient.name}, aliases: {ingredient.aliases}")

        db.commit()
        print(f"迁移完成！共迁移了 {migrated_count} 个食材的别名数据")

    except Exception as e:
        db.rollback()
        print(f"迁移过程中出现错误: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_aliases_to_name_variants()