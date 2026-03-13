#!/usr/bin/env python3
"""专门测试菜谱264中食用油的成本计算问题"""

import sqlite3
import json

def test_cost_calculation():
    """检查菜谱264的食用油成本计算问题"""

    conn = sqlite3.connect('./backend/data/livecalc.db')
    cursor = conn.cursor()

    print("=== 菜谱264食用油成本计算分析 ===")

    # 检查菜谱264的食用油食材
    print("\n1. 菜谱264中的食用油相关食材:")
    cursor.execute('''
        SELECT ri.id, ri.recipe_id, ri.ingredient_id, ri.quantity, i.name, u.abbreviation
        FROM recipe_ingredients ri
        JOIN ingredients i ON ri.ingredient_id = i.id
        LEFT JOIN units u ON ri.unit_id = u.id
        WHERE ri.recipe_id = 264 AND i.name LIKE "%油%"
        ORDER BY ri.id
    ''')
    oil_ingredients = cursor.fetchall()
    for ing in oil_ingredients:
        print(f"   - RI ID: {ing[0]}, Ing ID: {ing[2]}, Qty: {ing[3]}, Unit: {ing[5]}, Name: {ing[4]}")

    print(f"\n2. 检查ID为4的食用油是否有商品关联:")
    cursor.execute('''
        SELECT p.id, p.ingredient_id, p.name, p.brand
        FROM products p
        WHERE p.ingredient_id = 4
    ''')
    products = cursor.fetchall()
    if products:
        for product in products:
            print(f"   - Product ID: {product[0]}, Name: {product[2]}, Brand: {product[3]}")
    else:
        print("   - 没有找到与食用油关联的商品")

    print(f"\n3. 检查ID为4的食用油是否有价格记录:")
    cursor.execute('''
        SELECT pr.id, pr.product_id, pr.user_id, pr.price, pr.standard_quantity,
               pr.product_name, pr.recorded_at
        FROM product_records pr
        JOIN products p ON pr.product_id = p.id
        WHERE p.ingredient_id = 4
        ORDER BY pr.recorded_at DESC
    ''')
    records = cursor.fetchall()
    if records:
        for record in records:
            print(f"   - Record ID: {record[0]}, Price: ¥{record[3]}, Quantity: {record[4]}, Date: {record[6]}")
    else:
        print("   - 没有找到食用油的价格记录")

    # 检查是否通过名称匹配到了价格记录
    print(f"\n4. 检查是否通过名称匹配到价格记录:")
    cursor.execute('''
        SELECT pr.id, pr.product_id, pr.user_id, pr.price, pr.standard_quantity,
               pr.product_name, pr.recorded_at
        FROM product_records pr
        WHERE pr.product_name LIKE '%食用油%'
        ORDER BY pr.recorded_at DESC
    ''')
    name_match_records = cursor.fetchall()
    if name_match_records:
        for record in name_match_records:
            print(f"   - Name Match Record ID: {record[0]}, Name: {record[5]}, Price: ¥{record[3]}, Quantity: {record[4]}")
    else:
        print("   - 没有找到名称匹配的记录")

    print(f"\n5. 检查所有与'油'相关的商品价格记录:")
    cursor.execute('''
        SELECT pr.id, pr.product_id, pr.user_id, pr.price, pr.standard_quantity,
               pr.product_name, pr.recorded_at, p.ingredient_id
        FROM product_records pr
        LEFT JOIN products p ON pr.product_id = p.id
        WHERE pr.product_name LIKE '%油%'
        ORDER BY pr.recorded_at DESC
        LIMIT 10
    ''')
    oil_related_records = cursor.fetchall()
    for record in oil_related_records:
        ing_id = record[7] if record[7] else "None"
        print(f"   - Record ID: {record[0]}, Product ID: {record[1]}, Ing ID: {ing_id}, Name: {record[5]}, Price: ¥{record[3]}, Qty: {record[4]}")

    print(f"\n6. 检查菜谱264中其他食材的成本情况:")
    cursor.execute('''
        SELECT ri.id, ri.quantity, i.name, u.abbreviation
        FROM recipe_ingredients ri
        JOIN ingredients i ON ri.ingredient_id = i.id
        LEFT JOIN units u ON ri.unit_id = u.id
        WHERE ri.recipe_id = 264
        ORDER BY ri.id
        LIMIT 10
    ''')
    all_ingredients = cursor.fetchall()
    for ing in all_ingredients:
        print(f"   - Ing ID: {ing[0]}, Qty: {ing[1]}, Unit: {ing[3]}, Name: {ing[2]}")

    conn.close()

if __name__ == "__main__":
    test_cost_calculation()