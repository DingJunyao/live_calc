#!/usr/bin/env python3
"""测试API返回的数据格式"""

import os
import sys
from pathlib import Path

# 添加后端目录到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.recipe_service import calculate_recipe_cost
from app.models.recipe import Recipe

def test_recipe_cost_return():
    print("正在连接数据库...")

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 获取菜谱
        recipe = db.query(Recipe).filter(Recipe.id == 264).first()

        if not recipe:
            print("未找到菜谱ID为264")
            return

        print(f"菜谱: {recipe.name}")
        print(f"份数: {recipe.servings}")

        # 获取成本计算结果
        import asyncio
        cost_result = asyncio.run(calculate_recipe_cost(recipe.id, 1, db))
        if cost_result:
            print(f"\n总成本: {cost_result['total_cost']}")
            print("\n完整成本明细:")
            for item in cost_result['cost_breakdown']:
                if "食用油" in item['ingredient_name']:
                    print(f"  - {item}")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_recipe_cost_return()