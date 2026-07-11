"""过敏原分组种子脚本（命令行：清空重建）。

复用 ``app.services.allergen_seed`` 的 ALLERGEN_GROUPS 数据与 _create_groups 逻辑。
lifespan 启动时走幂等 ``ensure_allergen_groups``；本脚本走 destructive
清空重建，供开发者手动重跑（如调整分组定义后强制刷新）。

执行方式: python -X utf8 scripts/seed_allergen_groups.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///data/livecalc.db')

from app.core.database import SessionLocal
from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.services.allergen_seed import ALLERGEN_GROUPS, _create_groups


def seed_allergen_groups():
    """清空重建过敏原分组（destructive，命令行专用）。"""
    db = SessionLocal()
    try:
        # 1) 清理旧数据
        existing_count = db.query(BlacklistGroup).count()
        if existing_count > 0:
            print(f"🧹 清理 {existing_count} 个旧分组及关联映射...")
            db.query(BlacklistGroupIngredient).delete()
            db.query(BlacklistGroup).delete()
            db.flush()
            print("   已清理完成")

        # 2) 复用 services 的创建逻辑
        created, mappings, not_found = _create_groups(db)

        print(f"\n🎉 完成！共创建 {created} 个分组，关联 {mappings} 条原料映射。")
        if not_found:
            print(f"\n⚠️  以下原料未找到（共 {len(not_found)} 条）：")
            for msg in not_found:
                print("  " + msg)

    except Exception as e:
        db.rollback()
        print(f"❌ 发生错误：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🌰  过敏原分组种子脚本 - GB 7718-2025（清空重建）")
    print("=" * 60)
    seed_allergen_groups()
