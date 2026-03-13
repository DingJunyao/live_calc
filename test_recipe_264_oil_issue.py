#!/usr/bin/env python3
"""测试菜谱264中食用油重复导致的计算问题"""

import os
import sys
from pathlib import Path
import asyncio

# 添加后端目录到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.recipe_service import calculate_recipe_nutrition, calculate_recipe_cost
from app.models.recipe import Recipe

def test_recipe_264_issues():
    """测试菜谱264的计算问题"""
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

        print("\n--- 食用油相关食材 ---")
        oil_ingredients = []
        for ri in recipe.ingredients:
            if ri.ingredient and '油' in ri.ingredient.name:
                print(f"- 食材: {ri.ingredient.name}")
                print(f"  数量: {ri.quantity} (类型: {type(ri.quantity)})")
                print(f"  单位: {ri.unit.abbreviation if ri.unit else 'None'}")
                print(f"  食材ID: {ri.ingredient.id}")
                print(f"  备注: {ri.note}")
                oil_ingredients.append(ri)
                print()

        print(f"共找到 {len(oil_ingredients)} 个含'油'的食材")

        # 分别计算营养和成本
        print("\n--- 正常计算结果 ---")
        nutrition_result = asyncio.run(calculate_recipe_nutrition(recipe.id, db))
        if nutrition_result:
            print(f"总卡路里: {nutrition_result['total_calories']}")
            print(f"总蛋白质: {nutrition_result['total_protein']}")
            print(f"总脂肪: {nutrition_result['total_fat']}")
            print(f"总碳水化合物: {nutrition_result['total_carbs']}")

            print(f"\n每份卡路里: {nutrition_result['per_serving']['calories']}")
            print(f"每份蛋白质: {nutrition_result['per_serving']['protein']}")
            print(f"每份脂肪: {nutrition_result['per_serving']['fat']}")
            print(f"每份碳水化合物: {nutrition_result['per_serving']['carbs']}")

            # 检查脂肪含量是否异常
            if nutrition_result['total_fat'] > 100:  # 假设100g为异常高值
                print(f"\n⚠️ 警告：总脂肪含量异常高 ({nutrition_result['total_fat']}g)")
                print("这可能是由于重复计算食用油导致的")

        cost_result = asyncio.run(calculate_recipe_cost(recipe.id, 1, db))  # 使用用户ID 1
        if cost_result:
            print(f"\n总成本: {cost_result['total_cost']}")
            print(f"每份成本: {cost_result['cost_per_serving']}")
            print("\n成本明细:")
            for item in cost_result['cost_breakdown']:
                print(f"  - {item['ingredient_name']}: {item['quantity']} × {item['unit_price']} = {item['cost']}")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_recipe_264_issues()