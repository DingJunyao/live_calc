#!/usr/bin/env python3
"""测试导入服务"""
import sys
import os
import zipfile
import tempfile
sys.path.insert(0, os.path.dirname(__file__))

from app.services.recipe_import_service import RecipeImportService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 数据库连接
DATABASE_URL = "sqlite:///data/livecalc.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

import_service = RecipeImportService(db)

# 读取ZIP文件
with zipfile.ZipFile('/tmp/repo.zip', 'r') as zip_ref:
    # 蚝油三鲜菇文件
    file_path = 'HowToCook-master/dishes/vegetable_dish/蚝油三鲜菇/蚝油三鲜菇.md'

    print("=" * 60)
    print(f"测试解析文件: {file_path}")
    print("=" * 60)

    # 直接调用 _parse_recipe_file 方法
    recipe_data = import_service._parse_recipe_file(zip_ref, file_path)

    if recipe_data:
        print(f"\n菜谱名称: {recipe_data.get('name')}")
        print(f"分类: {recipe_data.get('category')}")
        print(f"来源: {recipe_data.get('source')}")

        ingredients = recipe_data.get('ingredients', [])
        print(f"\n原料数量: {len(ingredients)}")
        for i, ing in enumerate(ingredients[:5], 1):
            print(f"  {i}. {ing}")

        steps = recipe_data.get('cooking_steps', [])
        print(f"\n步骤数量: {len(steps)}")
        for i, step in enumerate(steps[:5], 1):
            print(f"  {i}. {step.get('content', 'N/A')}")
    else:
        print("解析失败！")

    print("\n" + "=" * 60)
