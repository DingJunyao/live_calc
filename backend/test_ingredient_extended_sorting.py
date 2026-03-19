#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试 ingredient_extended API 的排序功能"""

import os
import sys
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_db
from app.api.ingredient_extended import get_ingredients
from app.models.user import User
from sqlalchemy.orm import Session
from fastapi import Query

async def test_ingredient_extended_sorting():
    """测试 ingredient_extended 模块的排序功能"""
    print("=== 测试 ingredient_extended API 排序功能 ===")

    db = next(get_db())
    try:
        # 模拟 FastAPI 的 Query 参数
        class MockUser:
            id = 1

        # 测试按价格记录数量排序
        print("测试按价格记录数量排序...")
        result = await get_ingredients(
            skip=0,
            limit=20,
            search=None,
            category_id=None,
            sort_by="price_records",
            db=db,
            current_user=MockUser()
        )

        print(f"返回结果数量: {len(result.items)}")
        print("前10个原料:")
        for i, item in enumerate(result.items[:10]):
            print(f"  {i+1}. ID: {item['id']}, Name: {item['name']}")

        # 测试按创建时间排序（默认）
        print("\n测试按创建时间排序...")
        result = await get_ingredients(
            skip=0,
            limit=20,
            search=None,
            category_id=None,
            sort_by="created_at",
            db=db,
            current_user=MockUser()
        )

        print(f"返回结果数量: {len(result.items)}")
        print("前10个原料:")
        for i, item in enumerate(result.items[:10]):
            print(f"  {i+1}. ID: {item['id']}, Name: {item['name']}, Created: {item['created_at']}")

        # 测试按名称排序
        print("\n测试按名称排序...")
        result = await get_ingredients(
            skip=0,
            limit=20,
            search=None,
            category_id=None,
            sort_by="name",
            db=db,
            current_user=MockUser()
        )

        print(f"返回结果数量: {len(result.items)}")
        print("前10个原料:")
        for i, item in enumerate(result.items[:10]):
            print(f"  {i+1}. ID: {item['id']}, Name: {item['name']}")

    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_ingredient_extended_sorting())