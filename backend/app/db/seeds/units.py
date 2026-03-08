"""
单位数据初始化脚本
补充菜谱和原料中缺失的单位
"""
from app.core.database import SessionLocal
from app.models.unit import Unit, UnitConversion


def seed_units():
    """初始化/补充单位数据"""
    db = SessionLocal()

    try:
        # 定义需要补充的单位
        new_units = [
            # 注意："克"和"毫升"已经在数据库中（分别为ID 3和ID 5），不需要添加
            # 菜谱中的"克"对应 abbreviation="g"的单位
            # 菜谱中的"毫升"对应 abbreviation="mL"的单位

            # 体积单位
            {"name": "碗", "abbreviation": "碗", "unit_type": "volume", "si_factor": 0.300, "is_si_base": False, "is_common": True, "display_order": 25},

            # 计数单位 - 容器类
            {"name": "袋", "abbreviation": "袋", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 30},
            {"name": "罐", "abbreviation": "罐", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 31},
            {"name": "盒", "abbreviation": "盒", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 32},
            {"name": "包", "abbreviation": "包", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 33},

            # 计数单位 - 形状/数量类
            {"name": "根", "abbreviation": "根", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 40},
            {"name": "瓣", "abbreviation": "瓣", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 41},
            {"name": "块", "abbreviation": "块", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 42},
            {"name": "小块", "abbreviation": "小块", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 43},
            {"name": "片", "abbreviation": "片", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 44},
            {"name": "小片", "abbreviation": "小片", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 45},
            {"name": "粒", "abbreviation": "粒", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 46},
            {"name": "颗", "abbreviation": "颗", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 47},
            {"name": "枚", "abbreviation": "枚", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 48},
            {"name": "份", "abbreviation": "份", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 49},
            {"name": "滴", "abbreviation": "滴", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 50},
            {"name": "头", "abbreviation": "头", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 51},
            {"name": "朵", "abbreviation": "朵", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 52},
            {"name": "棵", "abbreviation": "棵", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 53},
            {"name": "株", "abbreviation": "株", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 54},
            {"name": "叶", "abbreviation": "叶", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 55},
            {"name": "节", "abbreviation": "节", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 56},
            {"name": "段", "abbreviation": "段", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 57},
            {"name": "条", "abbreviation": "条", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 58},
            {"name": "圈", "abbreviation": "圈", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 59},
            {"name": "撮", "abbreviation": "撮", "unit_type": "count", "si_factor": 1.0, "is_si_base": False, "is_common": True, "display_order": 60},
        ]

        added_count = 0
        skipped_count = 0

        for unit_data in new_units:
            # 检查单位是否已存在（按缩写）
            existing = db.query(Unit).filter(Unit.abbreviation == unit_data["abbreviation"]).first()
            if existing:
                print(f"跳过: 单位 '{unit_data['abbreviation']}' 已存在")
                skipped_count += 1
                continue

            # 创建新单位
            unit = Unit(**unit_data)
            db.add(unit)
            added_count += 1
            print(f"添加: {unit_data['name']} ({unit_data['abbreviation']}) - {unit_data['unit_type']}")

        db.commit()
        print(f"\n✅ 完成！添加 {added_count} 个单位，跳过 {skipped_count} 个已存在单位")

    except Exception as e:
        db.rollback()
        print(f"❌ 错误: {e}")
        raise
    finally:
        db.close()


def seed_conversions():
    """初始化/补充换算关系"""
    db = SessionLocal()

    try:
        # 首先获取所有单位（建立缩写->ID的映射）
        units = db.query(Unit).all()
        unit_map = {u.abbreviation: u.id for u in units}

        # 定义需要添加的换算关系
        # 注意：数据库中"克"的单位缩写是"g"，"毫升"的单位缩写是"mL"
        # 它们是同一个单位，不需要建立换算关系
        new_conversions = [
            # 如果需要添加其他换算关系，可以在这里添加
        ]

        added_count = 0
        skipped_count = 0

        for from_abbr, to_abbr, factor, is_bidirectional in new_conversions:
            if from_abbr not in unit_map:
                print(f"警告: 源单位 '{from_abbr}' 不存在")
                continue
            if to_abbr not in unit_map:
                print(f"警告: 目标单位 '{to_abbr}' 不存在")
                continue

            from_unit_id = unit_map[from_abbr]
            to_unit_id = unit_map[to_abbr]

            # 检查换算关系是否已存在
            existing = db.query(UnitConversion).filter(
                UnitConversion.from_unit_id == from_unit_id,
                UnitConversion.to_unit_id == to_unit_id
            ).first()

            if existing:
                print(f"跳过换算: {from_abbr} -> {to_abbr} 已存在")
                skipped_count += 1
                continue

            # 创建换算关系
            conversion = UnitConversion(
                from_unit_id=from_unit_id,
                to_unit_id=to_unit_id,
                conversion_factor=factor,
                is_bidirectional=is_bidirectional,
                precision=6
            )
            db.add(conversion)
            added_count += 1
            print(f"添加换算: {from_abbr} -> {to_abbr} ({factor})")

        db.commit()
        print(f"\n✅ 完成！添加 {added_count} 个换算关系，跳过 {skipped_count} 个已存在关系")

    except Exception as e:
        db.rollback()
        print(f"❌ 错误: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("第一步: 补充单位数据")
    print("=" * 50)
    seed_units()

    print("\n" + "=" * 50)
    print("第二步: 补充换算关系")
    print("=" * 50)
    seed_conversions()

    print("\n" + "=" * 50)
    print("全部完成！")
    print("=" * 50)
