#!/usr/bin/env python3
"""
测试后端的 ingredient_details 功能
"""

import sys
import os
# 将当前目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recipe_service import calculate_recipe_nutrition
from typing import Generator


async def test_ingredient_details():
    """测试 ingredient_details 功能"""

    # 获取数据库会话
    db_gen: Generator = get_db()
    db: Session = next(db_gen)

    try:
        # 测试任意一个存在的菜谱ID（如果不存在可以先创建一个测试菜谱）
        recipe_id = 1
        result = await calculate_recipe_nutrition(recipe_id, db)

        if result:
            print("✅ 营养计算成功")
            print(f"Keys in result: {list(result.keys())}")

            # 检查是否包含 ingredient_details
            if 'ingredient_details' in result:
                print(f"✅ ingredient_details 字段存在")
                print(f"ingredient_details 长度: {len(result['ingredient_details'])}")

                if result['ingredient_details']:
                    print("ingredient_details 示例:")
                    for i, item in enumerate(result['ingredient_details'][:2]):  # 只显示前2个
                        print(f"  {i+1}: {item}")
                else:
                    print("⚠️  ingredient_details 为空列表")
            else:
                print("❌ ingredient_details 字段不存在")

            # 检查其他关键字段
            for key in ['total_calories', 'per_serving_nutrition', 'total_nutrition']:
                if key in result:
                    print(f"✅ {key} 字段存在")
                else:
                    print(f"❌ {key} 字段不存在")
        else:
            print("❌ 营养计算失败 - 返回 None")
            print("可能的原因：")
            print("- 菜谱 ID 不存在")
            print("- 没有相关食材数据")
            print("- 没有营养数据")

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def main():
    await test_ingredient_details()


if __name__ == "__main__":
    asyncio.run(main())