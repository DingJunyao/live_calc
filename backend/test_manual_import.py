#!/usr/bin/env python3
"""手动导入测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.recipe_import_service import RecipeImportService
from app.models.recipe import Recipe, RecipeIngredient
from app.schemas.recipe import RecipeCreate, CookingStep, RecipeIngredientCreate
import traceback

# 数据库连接
DATABASE_URL = "sqlite:///data/livecalc.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # 模拟菜谱数据
    recipe_data = {
        'name': '测试菜谱123',
        'ingredients': [
            {'ingredient_name': '盐', 'quantity': '5', 'unit': 'g'},
            {'ingredient_name': '油', 'quantity': '10', 'unit': 'ml'}
        ],
        'cooking_steps': [
            {'step': 1, 'content': '第一步：准备食材'},
            {'step': 2, 'content': '第二步：炒菜'}
        ],
        'source': 'howtocook:test',
        'category': '测试分类',
        'tags': ['test'],
        'total_time_minutes': 30,
        'difficulty': 'simple',
        'servings': 1,
        'tips': ['这是测试菜谱']
    }

    print("=" * 60)
    print("测试手动导入")
    print("=" * 60)

    # 构建菜谱对象
    recipe_create = RecipeCreate(
        name=recipe_data['name'],
        source=recipe_data['source'],
        category=recipe_data['category'],
        tags=recipe_data['tags'],
        cooking_steps=[
            CookingStep(
                step=item.get('step', idx + 1),
                content=item['content'],
                duration_minutes=item.get('duration_minutes')
            ) for idx, item in enumerate(recipe_data.get('cooking_steps', []))
        ],
        ingredients=[
            RecipeIngredientCreate(
                ingredient_name=item['ingredient_name'],
                quantity=item.get('quantity', ''),
                unit=item.get('unit', '')
            ) for item in recipe_data.get('ingredients', [])
        ],
        total_time_minutes=recipe_data.get('total_time_minutes'),
        difficulty=recipe_data.get('difficulty', 'simple'),
        servings=recipe_data.get('servings', 1),
        tips=recipe_data.get('tips', [])
    )

    print(f"\nRecipeCreate 创建成功:")
    print(f"  名称: {recipe_create.name}")
    print(f"  分类: {recipe_create.category}")
    print(f"  步骤数: {len(recipe_create.cooking_steps)}")
    print(f"  原料数: {len(recipe_create.ingredients)}")

    print(f"\n步骤数据:")
    for i, step in enumerate(recipe_create.cooking_steps, 1):
        print(f"  {i}. step={step.step}, content={step.content}")

    # 创建菜谱
    db_recipe = Recipe(
        name=recipe_create.name,
        source=recipe_create.source,
        category=recipe_create.category,
        user_id=1,
        tags=recipe_create.tags,
        cooking_steps=[s.model_dump() for s in recipe_create.cooking_steps],
        total_time_minutes=recipe_create.total_time_minutes,
        difficulty=recipe_create.difficulty,
        servings=recipe_create.servings,
        tips=recipe_create.tips
    )

    print(f"\nRecipe 对象创建成功:")
    print(f"  cooking_steps 类型: {type(db_recipe.cooking_steps)}")
    print(f"  cooking_steps: {db_recipe.cooking_steps}")

    db.add(db_recipe)
    db.flush()

    print(f"\n菜谱已添加到数据库，ID: {db_recipe.id}")

    # 验证数据库中的数据
    db.refresh(db_recipe)
    print(f"\n数据库中的数据:")
    print(f"  cooking_steps: {db_recipe.cooking_steps}")

    db.commit()
    print("\n✅ 导入成功")

except Exception as e:
    print(f"\n❌ 导入失败: {e}")
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
