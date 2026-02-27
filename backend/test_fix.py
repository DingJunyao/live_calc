"""
测试脚本：验证API端点是否正常工作
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.recipe_import_service import RecipeImportService


def test_import_service():
    db = SessionLocal()

    try:
        # 创建服务实例
        service = RecipeImportService(db)

        # 测试 _match_or_create_ingredient 方法
        print("Testing _match_or_create_ingredient method...")
        ingredient_name = "test_ingredient"
        result = service._match_or_create_ingredient(ingredient_name)
        print(f"Created/Matched ingredient: {result}")

        print("Test completed successfully! The issue with 'aliases' keyword should be fixed.")

    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_import_service()