#!/usr/bin/env python3
"""
数据库初始化脚本 - 密度数据和计数单位质量关系
用于初始化液体调味品的密度数据和计数单位的质量转换数据
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models.ingredient_density import IngredientDensity
from app.models.nutrition import Ingredient
from app.models.unit import Unit


def initialize_ingredient_densities(session):
    """初始化食材密度数据"""
    print("开始初始化食材密度数据...")

    # 获取单位ID
    g_unit = session.query(Unit).filter(Unit.abbreviation == "g").first()
    ml_unit = session.query(Unit).filter(Unit.abbreviation == "mL").first()

    if not g_unit or not ml_unit:
        print("错误：无法找到 'g' 或 'mL' 单位！")
        return

    # 液体调味品密度数据（g/mL）
    # 数据来源：USDA、中国食物成分表等
    liquid_density_data = {
        # 调味品（按密度排序）
        "菜籽油": {"density": 0.92, "condition": "常温", "confidence": 0.95},
        "色拉油": {"density": 0.91, "condition": "常温", "confidence": 0.95},
        "花生油": {"density": 0.92, "condition": "常温", "confidence": 0.95},
        "玉米油": {"density": 0.92, "condition": "常温", "confidence": 0.95},
        "豆油": {"density": 0.92, "condition": "常温", "confidence": 0.95},
        "葵花籽油": {"density": 0.92, "condition": "常温", "confidence": 0.95},
        "橄榄油": {"density": 0.92, "condition": "常温", "confidence": 0.95},

        "生抽": {"density": 1.20, "condition": "常温", "confidence": 0.90},
        "老抽": {"density": 1.20, "condition": "常温", "confidence": 0.90},
        "酱油": {"density": 1.20, "condition": "常温", "confidence": 0.90},

        "蚝油": {"density": 1.10, "condition": "常温", "confidence": 0.90},
        "蒸鱼豉油": {"density": 1.12, "condition": "常温", "confidence": 0.85},
        "虾酱": {"density": 1.08, "condition": "常温", "confidence": 0.85},

        "料酒": {"density": 0.98, "condition": "常温", "confidence": 0.90},
        "黄酒": {"density": 0.99, "condition": "常温", "confidence": 0.90},
        "白酒": {"density": 0.95, "condition": "常温", "confidence": 0.85},

        "醋": {"density": 1.01, "condition": "常温", "confidence": 0.90},
        "米醋": {"density": 1.02, "condition": "常温", "confidence": 0.90},
        "白醋": {"density": 1.01, "condition": "常温", "confidence": 0.90},
        "陈醋": {"density": 1.02, "condition": "常温", "confidence": 0.90},

        "香油": {"density": 0.93, "condition": "常温", "confidence": 0.95},
        "芝麻油": {"density": 0.93, "condition": "常温", "confidence": 0.95},

        "番茄酱": {"density": 1.10, "condition": "常温", "confidence": 0.85},
        "辣椒酱": {"density": 1.08, "condition": "常温", "confidence": 0.85},
        "豆瓣酱": {"density": 1.08, "condition": "常温", "confidence": 0.85},

        "蜂蜜": {"density": 1.42, "condition": "常温", "confidence": 0.90},
        "炼乳": {"density": 1.04, "condition": "常温", "confidence": 0.90},
        "牛奶": {"density": 1.03, "condition": "常温", "confidence": 0.95},
        "酸奶": {"density": 1.05, "condition": "常温", "confidence": 0.95},

        # 调味酱料
        "沙拉酱": {"density": 1.10, "condition": "常温", "confidence": 0.85},
        "芥末酱": {"density": 1.05, "condition": "常温", "confidence": 0.80},
    }

    added_count = 0
    updated_count = 0
    skipped_count = 0

    for name, data in liquid_density_data.items():
        ingredient = session.query(Ingredient).filter(Ingredient.name == name).first()

        if not ingredient:
            print(f"⚠️  跳过（食材不存在）：{name}")
            skipped_count += 1
            continue

        # 检查是否已存在密度数据
        existing = session.query(IngredientDensity).filter(
            IngredientDensity.ingredient_id == ingredient.id,
            IngredientDensity.from_unit_id == ml_unit.id,
            IngredientDensity.to_unit_id == g_unit.id
        ).first()

        if existing:
            # 更新现有记录
            existing.density_value = data["density"]
            existing.condition = data["condition"]
            existing.confidence = data["confidence"]
            existing.source = "USDA + 中国食物成分表"
            updated_count += 1
            print(f"📝 更新密度：{name} = {data['density']} g/mL")
        else:
            # 插入新记录
            density = IngredientDensity(
                ingredient_id=ingredient.id,
                from_unit_id=ml_unit.id,
                to_unit_id=g_unit.id,
                density_value=data["density"],
                condition=data["condition"],
                confidence=data["confidence"],
                source="USDA + 中国食物成分表"
            )
            session.add(density)
            added_count += 1
            print(f"➕ 添加密度：{name} = {data['density']} g/mL")

    session.commit()

    print(f"\n✅ 密度数据初始化完成！")
    print(f"   新增：{added_count} 条")
    print(f"   更新：{updated_count} 条")
    print(f"   跳过：{skipped_count} 条")


def main():
    """主函数"""
    print("🔧 开始初始化数据库...")

    # 创建会话
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # 初始化密度数据
        initialize_ingredient_densities(session)

        print("\n🎉 数据初始化成功完成！")
    except Exception as e:
        print(f"\n❌ 初始化失败：{e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
