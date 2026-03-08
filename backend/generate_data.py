#!/usr/bin/env python3
"""
生成测试数据的脚本
老王亲自写的，别tm乱改！
"""
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Merchant, ProductRecord
from app.core.database import engine, SessionLocal, Base

# 商家类型和名称模板
merchant_types = ["超市", "菜市场", "便利店", "农贸市场", "生鲜超市", "连锁店", "百货店", "粮油店"]
merchant_prefixes = ["好邻居", "天天", "百佳", "永辉", "沃尔玛", "家乐福", "华润万家", "大润发", "物美", "人人乐"]
merchant_names = ["便民店", "生鲜店", "菜市场", "粮油店", "副食店", "水果店", "蔬菜店", "超市"]

# 中国城市名称
cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "武汉", "南京"]
districts = ["东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区", "通州区", "顺义区", "大兴区", "昌平区"]
streets = ["长安街", "王府井大街", "三里屯路", "国贸桥", "中关村大街", "西单大街", "建国门外大街", "金融街", "朝阳门外大街", "东直门外大街"]

# 商品ID范围（从数据库查询得到）
PRODUCT_IDS = list(range(1, 720))  # 有719个商品
UNIT_IDS = [1, 2, 3, 4, 5, 7, 8, 11, 12, 13, 18, 19, 20, 24, 33]  # 常用单位ID

USER_ID = 1  # billding用户的ID


def generate_merchants(session, count=100):
    """生成商家数据"""
    merchants = []

    for i in range(count):
        # 随机生成商家名称
        prefix = random.choice(merchant_prefixes)
        name_template = random.choice(merchant_names)
        merchant_name = f"{prefix}{name_template}-{i+1}"

        # 随机生成地址
        city = random.choice(cities)
        district = random.choice(districts)
        street = random.choice(streets)
        address = f"{city}{district}{street}{random.randint(1, 999)}号"

        # 随机生成坐标（基于中国大概范围）
        latitude = random.uniform(22.0, 53.0)
        longitude = random.uniform(73.0, 135.0)

        merchant = Merchant(
            user_id=USER_ID,
            name=merchant_name,
            address=address,
            latitude=latitude,
            longitude=longitude
        )
        session.add(merchant)
        merchants.append(merchant)

    session.commit()
    # 重新查询获取ID
    merchant_ids = [m.id for m in merchants]
    print(f"艹！成功插入{count}个商家数据！")
    return merchant_ids


def generate_price_records(session, merchant_ids, count=100):
    """生成价格记录数据"""
    records = []

    for i in range(count):
        # 随机选择商品和商家
        product_id = random.choice(PRODUCT_IDS)
        merchant_id = random.choice(merchant_ids)

        # 获取商品名称（简化处理，直接查询数据库）
        product = session.execute(
            text(f"SELECT name FROM products WHERE id = {product_id}")
        ).fetchone()

        if not product:
            continue

        product_name = product[0]

        # 随机生成价格（1-500元之间）
        price = round(random.uniform(1, 500), 2)

        # 随机生成数量和单位
        original_quantity = random.uniform(0.1, 10)
        original_unit_id = random.choice(UNIT_IDS)

        # 标准数量和单位（简化处理，假设转换比例为1:1）
        standard_quantity = original_quantity
        standard_unit_id = original_unit_id

        # 随机生成记录时间（最近30天内）
        recorded_at = datetime.now() - timedelta(days=random.randint(0, 30))

        record = ProductRecord(
            user_id=USER_ID,
            product_id=product_id,
            product_name=product_name,
            merchant_id=merchant_id,
            price=price,
            currency="CNY",
            original_quantity=original_quantity,
            original_unit_id=original_unit_id,
            standard_quantity=standard_quantity,
            standard_unit_id=standard_unit_id,
            record_type="purchase",
            exchange_rate=1.0,
            recorded_at=recorded_at
        )
        records.append(record)

    session.bulk_save_objects(records)
    session.commit()
    print(f"乖乖！成功插入{len(records)}条价格记录数据！")


def main():
    """主函数"""
    session = SessionLocal()

    try:
        # 获取现有商家ID
        print("老王开始获取现有商家数据...")
        merchant_ids = session.execute(
            text("SELECT id FROM merchants WHERE id > 1")
        ).fetchall()
        merchant_ids = [mid[0] for mid in merchant_ids]

        # 生成100条价格记录
        print("老王开始生成价格记录数据...")
        generate_price_records(session, merchant_ids, count=100)

        print("\n艹！所有数据生成完毕！老王我真厉害！")

    except Exception as e:
        print(f"艹！出错了：{e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    main()
