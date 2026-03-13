#!/usr/bin/env python3
"""检查菜谱ID为264的详细信息"""

import os
import sys
from pathlib import Path

# 添加后端目录到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.config import settings

def check_recipe_264():
    """检查菜谱ID为264的详细信息"""
    print("正在连接数据库...")

    # 使用相同的数据库URL
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 查询菜谱ID为264
        recipe = db.query(Recipe).filter(Recipe.id == 264).first()

        if not recipe:
            print("未找到菜谱ID为264的记录")
            return

        print(f"找到菜谱: {recipe.id} - {recipe.name}")
        print(f"描述: {recipe.description}")
        print(f"份数: {recipe.servings}")
        print(f"创建时间: {recipe.created_at}")
        print(f"更新时间: {recipe.updated_at}")

        print("\n--- 菜谱食材 ---")
        for recipe_ingredient in recipe.ingredients:
            ingredient = recipe_ingredient.ingredient
            print(f"- 食材ID: {ingredient.id if ingredient else 'None'}")
            print(f"  名称: {ingredient.name if ingredient else 'None'}")
            print(f"  数量: {recipe_ingredient.quantity}")
            print(f"  单位: {recipe_ingredient.unit.abbreviation if recipe_ingredient.unit else 'None'}")
            print(f"  备注: {recipe_ingredient.notes}")
            print()

        # 特别关注包含"油"的食材
        oil_ingredients = [ri for ri in recipe.ingredients
                          if ri.ingredient and '油' in ri.ingredient.name]
        if oil_ingredients:
            print("--- 包含'油'的食材 ---")
            for ri in oil_ingredients:
                ingredient = ri.ingredient
                print(f"- 食材: {ingredient.name}")
                print(f"  数量: {ri.quantity} {ri.unit.abbreviation if ri.unit else ''}")
                print()
        else:
            print("--- 没有找到包含'油'的食材 ---")

    except Exception as e:
        print(f"查询过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_recipe_264()