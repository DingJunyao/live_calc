"""
能量营养素键名统一迁移脚本

将营养数据 JSON 中的 energy_kcal / energy_kcal_alt 统一为 energy。

背景：USDA 导入曾因源字段命名差异，将能量分别映射成 energy（来自"能量/Energy"）、
energy_kcal（Atwater 通用系数）、energy_kcal_alt（Atwater 特定系数）三个键，
导致同一营养素分裂、展示/编辑/计算链路行为不一致。现已将导入映射与全系统统一为
energy，本脚本用于迁移历史数据。

处理范围：
  - nutrition_data.nutrients
  - products.custom_nutrition_data

处理逻辑（对 core_nutrients / all_nutrients / nutrient_details 每层）：
  - 若存在 energy_kcal 或 energy_kcal_alt，且 energy 不存在 → 重命名为 energy
  - 若 energy 已存在 → 删除冗余的 energy_kcal / energy_kcal_alt（energy 优先）

特性：幂等，可重复执行；支持 --dry-run 预览。

用法：
  cd backend
  ../.venv/Scripts/python scripts/migrate_energy_keys.py [--dry-run]

注：由于是 JSON 内嵌套键名替换 + 冲突合并（非表结构变更），采用 Python 脚本
统一处理，跨 SQLite/MySQL/PostgreSQL 通用，逻辑清晰可审计。
"""
import sys
import argparse

sys.path.insert(0, '.')

from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.models.nutrition_data import NutritionData
from app.models.product_entity import Product

# 需统一的源键（按优先级：energy_kcal 优先于 energy_kcal_alt）
SOURCE_KEYS = ['energy_kcal', 'energy_kcal_alt']
TARGET_KEY = 'energy'


def migrate_layer(layer) -> bool:
    """处理单个营养素字典层（如 all_nutrients），返回是否有变更。

    两类处理：
      1. 键名统一：energy_kcal/energy_kcal_alt 键 → energy（energy 已存在则删冗余）
      2. 条目内 key 字段值统一：core_nutrients 用中文键，但每个条目的 "key" 字段
         标识英文键名（如 core_nutrients["能量"]["key"]="energy_kcal"），需一并改为 energy
    """
    if not isinstance(layer, dict):
        return False

    changed = False

    # 1. 键名统一：energy 优先
    if TARGET_KEY in layer:
        for src in SOURCE_KEYS:
            if src in layer:
                del layer[src]
                changed = True
    else:
        for src in SOURCE_KEYS:
            if src in layer:
                layer[TARGET_KEY] = layer.pop(src)
                changed = True
                break
        for src in SOURCE_KEYS:
            if src in layer:
                del layer[src]
                changed = True

    # 2. 条目内 key 字段值统一
    for entry in layer.values():
        if isinstance(entry, dict) and entry.get('key') in SOURCE_KEYS:
            entry['key'] = TARGET_KEY
            changed = True

    return changed


def migrate_nutrients(nutrients) -> bool:
    """处理 nutrients JSON 的三层结构，返回是否有变更。"""
    if not isinstance(nutrients, dict):
        return False
    changed = False
    for layer_key in ('core_nutrients', 'all_nutrients', 'nutrient_details'):
        if layer_key in nutrients:
            if migrate_layer(nutrients[layer_key]):
                changed = True
    return changed


def main():
    parser = argparse.ArgumentParser(description='统一能量营养素键名为 energy')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不写入数据库')
    args = parser.parse_args()

    db = SessionLocal()
    try:
        nd_changed = 0
        for nd in db.query(NutritionData).all():
            if migrate_nutrients(nd.nutrients):
                flag_modified(nd, 'nutrients')
                nd_changed += 1

        prod_changed = 0
        for p in db.query(Product).all():
            if p.custom_nutrition_data and migrate_nutrients(p.custom_nutrition_data):
                flag_modified(p, 'custom_nutrition_data')
                prod_changed += 1

        if args.dry_run:
            db.rollback()
            print(f"[DRY-RUN] 预览：nutrition_data 需迁移 {nd_changed} 条，products 需迁移 {prod_changed} 条（未写入）")
        else:
            db.commit()
            print(f"迁移完成：nutrition_data {nd_changed} 条，products {prod_changed} 条")
    except Exception as e:
        db.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
