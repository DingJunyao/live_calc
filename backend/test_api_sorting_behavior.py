#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试API端点行为"""

import requests
import json

def test_api_sorting():
    """测试API的排序行为"""
    # 测试API端点
    url = "http://localhost:8000/api/v1/nutrition/ingredients?skip=0&limit=20&sort_by=price_records"

    try:
        response = requests.get(url, headers={
            'accept': 'application/json',
            'Authorization': 'Bearer YOUR_TOKEN_HERE'  # 需要有效的token
        })

        if response.status_code == 200:
            data = response.json()
            print("API Response successful!")
            print(f"Total items: {data.get('total', 0)}")

            items = data.get('items', [])
            print(f"Retrieved {len(items)} items:")

            for i, item in enumerate(items[:10]):  # 只打印前10个
                print(f"{i+1}. ID: {item.get('id')}, Name: {item.get('name')}")

        else:
            print(f"API request failed with status {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Error testing API: {e}")
        print("Note: This test requires the FastAPI server to be running with proper authentication")


def check_direct_db_query():
    """再次检查数据库查询逻辑"""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    from app.core.database import get_db
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    from app.models.nutrition import Ingredient
    from sqlalchemy import func

    print("\n=== 手动验证数据库查询逻辑 ===")

    db = next(get_db())
    try:
        # 执行与API中相同的查询逻辑
        subquery = db.query(
            Ingredient.id.label('ingredient_id'),
            func.coalesce(func.count(ProductRecord.id), 0).label('record_count')
        ).outerjoin(
            Product, Ingredient.id == Product.ingredient_id
        ).outerjoin(
            ProductRecord, Product.id == ProductRecord.product_id
        ).filter(Ingredient.is_active == True).group_by(Ingredient.id).subquery()

        # 然后将此子查询与主查询连接，并按记录数量排序
        query = db.query(Ingredient).join(
            subquery, Ingredient.id == subquery.c.ingredient_id
        ).filter(Ingredient.is_active == True)

        # 按价格记录数量降序排列
        ingredients = query.order_by(
            subquery.c.record_count.desc(),  # 按记录数量降序排列
            Ingredient.id  # 按ID确保排序稳定性
        ).limit(20).all()

        print("Manual DB query results (first 20):")
        for idx, ing in enumerate(ingredients):
            # 重新查询每个原料的价格记录数量以便显示
            record_count = db.query(func.count(ProductRecord.id)).join(
                Product, Product.id == ProductRecord.product_id
            ).filter(Product.ingredient_id == ing.id).scalar()

            print(f'{idx+1}. ID: {ing.id}, Name: {ing.name}, Records: {record_count}')

    finally:
        db.close()


if __name__ == "__main__":
    print("Testing sorting logic...")
    check_direct_db_query()