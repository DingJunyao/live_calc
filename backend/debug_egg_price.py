#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""深入调查鸡蛋价格计算问题"""

import os
import sys
from decimal import Decimal

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_db
from app.models.product_entity import Product
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient
from sqlalchemy import func
from datetime import datetime, timedelta

def debug_egg_price_calculation():
    """详细调试鸡蛋的价格计算过程"""
    print("=== 调试鸡蛋价格计算过程 ===")

    db = next(get_db())
    try:
        # 找到鸡蛋原料
        egg_ingredient = db.query(Ingredient).filter(
            Ingredient.name.like('%鸡蛋%')
        ).first()

        if not egg_ingredient:
            print("未找到鸡蛋原料")
            return

        print(f"鸡蛋原料ID: {egg_ingredient.id}, 名称: {egg_ingredient.name}")

        # 获取鸡蛋关联的商品
        products = db.query(Product).filter(
            Product.ingredient_id == egg_ingredient.id
        ).all()

        print(f"关联商品数量: {len(products)}")
        for p in products:
            print(f"  - 商品ID: {p.id}, 名称: {p.name}")

        if not products:
            print("未找到关联商品")
            return

        product_ids = [p.id for p in products]

        # 获取所有相关价格记录
        all_records = db.query(ProductRecord).filter(
            ProductRecord.product_id.in_(product_ids)
        ).order_by(ProductRecord.recorded_at.desc()).all()

        print(f"\n总共找到 {len(all_records)} 条价格记录")
        for i, record in enumerate(all_records[:10]):  # 只打印前10条
            print(f"  {i+1}. 记录ID: {record.id}, 价格: {record.price}, 数量: {record.original_quantity}, "
                  f"单位: {record.original_unit.name if record.original_unit else 'N/A'}, "
                  f"时间: {record.recorded_at.strftime('%Y-%m-%d %H:%M:%S') if record.recorded_at else 'N/A'}")

        # 检查是否有近期记录（最近7天）
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_records = [r for r in all_records if r.recorded_at >= seven_days_ago]

        print(f"\n最近7天内记录数: {len(recent_records)}")
        for i, record in enumerate(recent_records):
            unit_price = record.price / record.original_quantity if record.original_quantity and record.original_quantity > 0 else 0
            print(f"  {i+1}. 记录ID: {record.id}, 总价: {record.price}, 数量: {record.original_quantity}, "
                  f"单价: {unit_price:.4f}, 单位: {record.original_unit.name if record.original_unit else 'N/A'}")

        # 检查最近一条记录
        if all_records:
            latest = all_records[0]
            print(f"\n最近一条记录:")
            print(f"  - 价格: {latest.price}")
            print(f"  - 数量: {latest.original_quantity}")
            if latest.original_quantity and latest.original_quantity > 0:
                unit_price = latest.price / latest.original_quantity
                print(f"  - 计算单价: {latest.price} / {latest.original_quantity} = {unit_price:.4f}")
            else:
                print("  - 无法计算单价（数量为0或None）")

        # 检查今天的数据
        today = datetime.utcnow().date()
        today_records = [r for r in all_records if r.recorded_at.date() == today]

        print(f"\n今天的记录数: {len(today_records)}")
        for i, record in enumerate(today_records):
            unit_price = record.price / record.original_quantity if record.original_quantity and record.original_quantity > 0 else 0
            print(f"  {i+1}. 记录ID: {record.id}, 总价: {record.price}, 数量: {record.original_quantity}, "
                  f"单价: {unit_price:.4f}")

    finally:
        db.close()


def debug_specific_product_price():
    """调试特定商品的价格计算"""
    print("\n=== 调试特定商品的价格计算 ===")

    db = next(get_db())
    try:
        # 如果知道具体商品ID，可以针对性调试
        # 从之前的测试我们知道商品ID为2是鸡蛋相关商品
        product_id = 2

        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            print(f"商品ID {product_id}: {product.name}, 关联原料: {product.ingredient.name if product.ingredient else 'N/A'}")

        # 获取该商品的所有记录
        records = db.query(ProductRecord).filter(
            ProductRecord.product_id == product_id
        ).order_by(ProductRecord.recorded_at.desc()).all()

        print(f"商品ID {product_id} 有 {len(records)} 条记录")
        for i, record in enumerate(records):
            unit_price = record.price / record.original_quantity if record.original_quantity and record.original_quantity > 0 else 0
            print(f"  {i+1}. 总价: {record.price}, 数量: {record.original_quantity}, 单价: {unit_price:.4f}, 时间: {record.recorded_at}")

    finally:
        db.close()


if __name__ == "__main__":
    debug_egg_price_calculation()
    debug_specific_product_price()