"""
迁移脚本：将 name_variants 字段迁移为 aliases 字段

数据结构变化：
  旧格式: name_variants = {"aliases": ["土豆", "马铃薯"], "region_specific": {"北方": ["土豆"], "南方": ["洋芋"]}}
  新格式: aliases = ["土豆", "马铃薯", "洋芋"]

使用方法：
  1. 先运行 SQL 脚本添加新字段（如果字段不存在）：
     ALTER TABLE ingredients ADD COLUMN aliases TEXT;

  2. 运行此 Python 脚本迁移数据：
     cd backend && python migrate_name_variants_to_aliases.py

  3. 确认迁移成功后，可删除旧字段（可选）：
     ALTER TABLE ingredients DROP COLUMN name_variants;
"""

import json
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models.nutrition import Ingredient


def check_column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    if "sqlite" in str(engine.url):
        # SQLite 查询表结构
        result = engine.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result]
        return column_name in columns
    else:
        # PostgreSQL/MySQL 查询表结构
        result = engine.execute(text(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """))
        return result.fetchone() is not None


def add_aliases_column():
    """添加 aliases 列（如果不存在）"""
    if check_column_exists("ingredients", "aliases"):
        print("aliases 列已存在，跳过创建")
        return True

    try:
        if "sqlite" in str(engine.url):
            engine.execute(text("ALTER TABLE ingredients ADD COLUMN aliases TEXT"))
        else:
            engine.execute(text("ALTER TABLE ingredients ADD COLUMN aliases JSON"))
        print("成功添加 aliases 列")
        return True
    except Exception as e:
        print(f"添加 aliases 列失败: {e}")
        return False


def extract_all_aliases(name_variants: dict) -> list:
    """从 name_variants 结构中提取所有别名"""
    aliases = set()

    if not name_variants:
        return []

    # 提取主别名列表
    if "aliases" in name_variants:
        main_aliases = name_variants["aliases"]
        if isinstance(main_aliases, list):
            aliases.update(main_aliases)
        elif main_aliases:
            aliases.add(str(main_aliases))

    # 提取地区特定别名
    if "region_specific" in name_variants:
        region_data = name_variants["region_specific"]
        if isinstance(region_data, dict):
            for region, regional_aliases in region_data.items():
                if isinstance(regional_aliases, list):
                    aliases.update(regional_aliases)
                elif regional_aliases:
                    aliases.add(str(regional_aliases))

    # 返回去重后的列表
    return list(aliases)


def migrate_name_variants_to_aliases():
    """执行迁移"""
    db = SessionLocal()

    try:
        # 1. 确保列存在
        if not check_column_exists("ingredients", "aliases"):
            print("aliases 列不存在，请先运行 SQL 脚本添加列")
            return False

        # 2. 查询所有食材
        ingredients = db.query(Ingredient).all()

        migrated_count = 0
        skipped_count = 0

        for ingredient in ingredients:
            # 检查是否已经有 aliases 数据
            if ingredient.aliases is not None and len(ingredient.aliases) > 0:
                skipped_count += 1
                continue

            # 检查是否有旧的 name_variants 数据
            name_variants = None
            if hasattr(ingredient, 'name_variants') and ingredient.name_variants is not None:
                name_variants = ingredient.name_variants

            if name_variants:
                # 解析 name_variants 并提取所有别名
                if isinstance(name_variants, str):
                    try:
                        name_variants = json.loads(name_variants)
                    except json.JSONDecodeError:
                        name_variants = None

                if isinstance(name_variants, dict):
                    extracted_aliases = extract_all_aliases(name_variants)
                    if extracted_aliases:
                        ingredient.aliases = extracted_aliases
                        migrated_count += 1
                        print(f"迁移: {ingredient.name} -> aliases: {extracted_aliases}")

        # 3. 提交更改
        db.commit()
        print(f"\n迁移完成!")
        print(f"  - 成功迁移: {migrated_count} 个食材")
        print(f"  - 跳过（已有数据）: {skipped_count} 个食材")

        return True

    except Exception as e:
        db.rollback()
        print(f"迁移过程中出现错误: {str(e)}")
        raise
    finally:
        db.close()


def verify_migration():
    """验证迁移结果"""
    db = SessionLocal()

    try:
        ingredients = db.query(Ingredient).filter(Ingredient.aliases.isnot(None)).limit(10).all()

        print("\n验证结果（前10条有 aliases 的记录）:")
        print("-" * 60)
        for ing in ingredients:
            print(f"ID: {ing.id}, 名称: {ing.name}")
            print(f"  aliases: {ing.aliases}")
            if hasattr(ing, 'name_variants') and ing.name_variants:
                print(f"  name_variants: {ing.name_variants}")
            print()

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("name_variants -> aliases 迁移脚本")
    print("=" * 60)
    print()

    # 执行迁移
    if migrate_name_variants_to_aliases():
        # 验证结果
        verify_migration()