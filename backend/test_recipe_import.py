from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recipe_import_service import RecipeImportService
from unittest.mock import patch, MagicMock
import tempfile
import zipfile
import json


def test_recipe_import():
    """
    测试菜谱导入功能
    """
    print("开始测试菜谱导入功能...")

    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        # 创建一个简单的测试用菜谱数据
        test_recipe_data = {
            "name": "测试菜谱",
            "ingredients": [
                {"ingredient_name": "鸡蛋", "quantity": "2", "unit": "个"},
                {"ingredient_name": "番茄", "quantity": "1", "unit": "个"}
            ],
            "cooking_steps": [
                {"step": 1, "content": "打鸡蛋"},
                {"step": 2, "content": "切番茄"}
            ],
            "source": "test-source",
            "tags": ["测试", "简单"],
            "servings": 2
        }

        # 模拟从远程仓库导入
        import_service = RecipeImportService(db)

        # 测试 _normalize_recipe_data 方法
        normalized = import_service._normalize_recipe_data(test_recipe_data, "test/recipe.json")
        print(f"标准化菜谱数据: {normalized}")

        if normalized:
            print("✓ 菜谱数据标准化测试通过")
        else:
            print("✗ 菜谱数据标准化测试失败")

        print("菜谱导入功能测试完成!")

    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    test_recipe_import()