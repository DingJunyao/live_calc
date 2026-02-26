import asyncio
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recipe_import_service import check_and_import_initial_recipes


def initialize_app():
    """
    初始化应用，包括导入初始菜谱
    """
    print("开始初始化应用...")

    try:
        # 获取数据库会话
        db_gen = get_db()
        db: Session = next(db_gen)

        print("检查并导入初始菜谱...")
        result = check_and_import_initial_recipes(db)
        print(f"初始菜谱导入结果: {result}")

        # 关闭数据库会话
        db.close()
        print("应用初始化完成!")

    except Exception as e:
        print(f"应用初始化过程中发生错误: {str(e)}")
        raise


if __name__ == "__main__":
    initialize_app()