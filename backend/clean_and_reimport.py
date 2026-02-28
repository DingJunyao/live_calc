#!/usr/bin/env python3
"""
清理并重新导入 HowToCook 菜谱
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.recipe import Recipe, RecipeIngredient
from app.services.recipe_import_service import RecipeImportService

# 数据库连接
DATABASE_URL = "sqlite:///data/livecalc.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def clean_howtocook_recipes():
    """删除所有来自 howtocook 的菜谱"""
    print("正在清理 HowToCook 菜谱...")
    db = SessionLocal()

    try:
        # 查询所有来自 howtocook 的菜谱
        recipes = db.query(Recipe).filter(Recipe.source.like('howtocook:%')).all()

        count = len(recipes)
        print(f"找到 {count} 个 HowToCook 菜谱")

        # 删除这些菜谱（由于设置了 cascade="all, delete-orphan"，原料关联会自动删除）
        for recipe in recipes:
            db.delete(recipe)

        db.commit()
        print(f"已删除 {count} 个 HowToCook 菜谱")
        return count

    except Exception as e:
        db.rollback()
        print(f"清理失败: {e}")
        return 0
    finally:
        db.close()

def reimport_recipes():
    """重新导入菜谱"""
    print("\n开始重新导入菜谱...")
    db = SessionLocal()

    try:
        import_service = RecipeImportService(db)
        result = import_service.import_recipes_from_cook_repo()

        print(f"\n导入结果:")
        print(f"  成功: {result.get('imported_count', 0)}")
        print(f"  失败/跳过: {result.get('failed_count', 0)}")

        if result.get('errors'):
            print(f"\n跳过或失败的菜谱:")
            for error in result.get('errors', [])[:20]:  # 显示前20个
                print(f"  - {error}")
            if len(result.get('errors', [])) > 20:
                print(f"  ... 还有 {len(result.get('errors', [])) - 20} 个")

        return result

    except Exception as e:
        print(f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 60)
    print("HowToCook 菜谱清理和重新导入工具")
    print("=" * 60)

    # 清理旧菜谱
    deleted_count = clean_howtocook_recipes()

    if deleted_count > 0:
        # 重新导入
        result = reimport_recipes()

        if result and result.get('success'):
            print("\n✅ 清理和重新导入完成！")
        else:
            print("\n❌ 重新导入失败！")
    else:
        print("\n没有找到需要清理的菜谱")

    print("=" * 60)

if __name__ == "__main__":
    main()