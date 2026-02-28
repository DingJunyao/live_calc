#!/usr/bin/env python3
"""测试蜂蜜面包解析"""
import sys
import os
import zipfile
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
    # 无厨师机蜂蜜面包文件
    file_path = 'HowToCook-master/dishes/dessert/无厨师机蜂蜜面包/无厨师机蜂蜜面包.md'

    print("=" * 60)
    print(f"测试解析文件: {file_path}")
    print("=" * 60)

    # 直接调用 _parse_recipe_file 方法
    recipe_data = import_service._parse_recipe_file(zip_ref, file_path)

    if recipe_data:
        print(f"\n菜谱名称: {recipe_data.get('name')}")

        ingredients = recipe_data.get('ingredients', [])
        print(f"\n原料数量: {len(ingredients)}")
        for i, ing in enumerate(ingredients[:15], 1):
            print(f"  {i}. {ing}")
    else:
        print("解析失败！")

    print("\n" + "=" * 60)
