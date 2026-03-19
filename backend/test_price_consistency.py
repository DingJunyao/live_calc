#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试价格计算逻辑的一致性"""

import os
import sys
import asyncio
from decimal import Decimal

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_db
from app.models.product_entity import Product
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient
from sqlalchemy import func, desc
from datetime import datetime, timedelta

def test_ingredient_price_calculation():
    """测试原料价格计算逻辑"""
    print("测试原料价格计算逻辑...")

    db = next(get_db())
    try:
        # 模拟 API 中的逻辑
        ingredient_id = 2  # 假设鸡蛋的ID是2

        # 获取该原料关联的商品
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).all()

        if not products:
            print("未找到关联商品")
            return

        product_ids = [p.id for p in products]
        print(f"关联商品ID: {product_ids}")

        # 首先尝试获取最近24小时内的记录
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)

        recent_records = db.query(ProductRecord).filter(
            ProductRecord.product_id.in_(product_ids),
            ProductRecord.recorded_at >= one_day_ago
        ).order_by(ProductRecord.recorded_at.desc()).all()

        print(f"最近24小时内记录数: {len(recent_records)}")

        # 如果最近24小时内没有记录，则查找最近一次记录的那一天的所有记录
        if not recent_records:
            # 查找最近一次记录
            latest_record = db.query(ProductRecord).filter(
                ProductRecord.product_id.in_(product_ids)
            ).order_by(ProductRecord.recorded_at.desc()).first()

            if not latest_record:
                print("没有价格记录")
                return

            # 获取与最近记录同一天的所有记录
            latest_date = latest_record.recorded_at.date()
            recent_records = db.query(ProductRecord).filter(
                ProductRecord.product_id.in_(product_ids),
                func.date(ProductRecord.recorded_at) == latest_date
            ).all()

            print(f"最近记录日期 {latest_date} 的记录数: {len(recent_records)}")

        if not recent_records:
            print("没有找到相关记录")
            return

        # 计算平均价格 - 使用单价而非总价
        unit_prices = []
        for record in recent_records:
            if record.price is not None and record.original_quantity is not None and record.original_quantity > 0:
                # 计算单价：总价 / 数量
                unit_price = record.price / record.original_quantity
                unit_prices.append(unit_price)
                print(f"记录ID: {record.id}, 总价: {record.price}, 数量: {record.original_quantity}, 单价: {unit_price}")

        if not unit_prices:
            print("没有有效的单价记录")
            return

        average_price = sum(unit_prices) / len(unit_prices)
        print(f"平均单价: {average_price}")

    finally:
        db.close()


def test_product_price_calculation():
    """测试商品价格计算逻辑"""
    print("\n测试商品价格计算逻辑...")

    db = next(get_db())
    try:
        product_id = 1  # 假设第一个商品

        # 查询该商品的所有价格记录
        all_records = db.query(ProductRecord).filter(
            ProductRecord.product_id == product_id
        ).order_by(ProductRecord.recorded_at.desc()).all()

        if not all_records:
            print("商品没有价格记录")
            return

        print(f"商品价格记录总数: {len(all_records)}")

        # 首先尝试获取最近24小时内的记录
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)

        recent_records = [r for r in all_records if r.recorded_at >= one_day_ago]

        # 如果最近24小时内没有记录，则查找最近一次记录的那一天的所有记录
        if not recent_records:
            # 最近一次记录的日期
            latest_date = all_records[0].recorded_at.date()
            recent_records = [r for r in all_records if r.recorded_at.date() == latest_date]

        if not recent_records:
            print("没有最近的记录")
            return

        print(f"最近记录数: {len(recent_records)}")

        # 计算平均价格 - 使用单价而非总价
        unit_prices = []
        for record in recent_records:
            if record.price is not None and record.original_quantity is not None and record.original_quantity > 0:
                # 计算单价：总价 / 数量
                unit_price = record.price / record.original_quantity
                unit_prices.append(unit_price)
                print(f"记录ID: {record.id}, 总价: {record.price}, 数量: {record.original_quantity}, 单价: {unit_price}")

        if not unit_prices:
            print("没有有效的单价记录")
            return

        average_price = sum(unit_prices) / len(unit_prices)
        print(f"商品平均单价: {average_price}")

    finally:
        db.close()


def test_ingredients_sorting():
    """测试原料列表排序逻辑"""
    print("\n测试原料列表排序逻辑...")

    db = next(get_db())
    try:
        # 按价格记录数量排序的子查询
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

        print("按价格记录数量排序的前20个原料:")
        for idx, ing in enumerate(ingredients):
            # 重新查询每个原料的价格记录数量以便显示
            record_count = db.query(func.count(ProductRecord.id)).join(
                Product, Product.id == ProductRecord.product_id
            ).filter(Product.ingredient_id == ing.id).scalar()

            print(f'{idx+1}. ID: {ing.id}, Name: {ing.name}, Records: {record_count}')

    finally:
        db.close()


if __name__ == "__main__":
    test_ingredient_price_calculation()
    test_product_price_calculation()
    test_ingredients_sorting()