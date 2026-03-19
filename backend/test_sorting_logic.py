#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试原料列表的排序逻辑"""

from app.core.database import get_db
from app.models.nutrition import Ingredient
from app.models.product import ProductRecord
from app.models.product_entity import Product
from sqlalchemy import func


def test_sorting_logic():
    """测试按价格记录数量排序的逻辑"""
    db = next(get_db())
    try:
        print("测试按价格记录数量排序的逻辑...")

        # 模拟构建子查询（与API中相同的逻辑）
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

        print('Top 20 ingredients by price record count (direct DB query):')
        for idx, ing in enumerate(ingredients):
            # 重新查询每个原料的价格记录数量以便显示
            record_count = db.query(func.count(ProductRecord.id)).join(
                Product, Product.id == ProductRecord.product_id
            ).filter(Product.ingredient_id == ing.id).scalar()

            print(f'{idx+1}. ID: {ing.id}, Name: {ing.name}, Records: {record_count}')

        # 特别查看鸡蛋的位置
        egg_found = False
        egg_idx = 0
        for idx, ing in enumerate(ingredients):
            if '鸡蛋' in ing.name:
                print(f'鸡蛋在第 {idx+1} 位 (ID: {ing.id})')
                egg_found = True
                break

        if not egg_found:
            print('鸡蛋不在前20名中')

    finally:
        db.close()


if __name__ == "__main__":
    test_sorting_logic()