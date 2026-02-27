"""
直接使用SQL更新数据库表结构的脚本
"""

import sqlite3
import os

def update_database_schema():
    db_path = "data/livecalc.db"

    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查ingredients表是否有新的列
        cursor.execute("PRAGMA table_info(ingredients)")
        columns = [column[1] for column in cursor.fetchall()]

        # 添加缺失的列
        if 'category_id' not in columns:
            cursor.execute("ALTER TABLE ingredients ADD COLUMN category_id INTEGER")
            print("Added category_id column to ingredients table")

        if 'density' not in columns:
            cursor.execute("ALTER TABLE ingredients ADD COLUMN density REAL")
            print("Added density column to ingredients table")

        if 'default_unit' not in columns:
            cursor.execute("ALTER TABLE ingredients ADD COLUMN default_unit TEXT")
            print("Added default_unit column to ingredients table")

        if 'name_variants' not in columns:
            cursor.execute("ALTER TABLE ingredients ADD COLUMN name_variants TEXT")  # JSON as text in SQLite
            print("Added name_variants column to ingredients table")

        if 'updated_at' not in columns:
            cursor.execute("ALTER TABLE ingredients ADD COLUMN updated_at DATETIME")
            print("Added updated_at column to ingredients table")

        # 更新nutrition_data表添加新的字段
        cursor.execute("PRAGMA table_info(nutrition_data)")
        nd_columns = [column[1] for column in cursor.fetchall()]

        if 'nutrients' not in nd_columns:
            cursor.execute("ALTER TABLE nutrition_data ADD COLUMN nutrients TEXT")  # JSON as text in SQLite
            print("Added nutrients column to nutrition_data table")

        if 'serving_size' not in nd_columns:
            cursor.execute("ALTER TABLE nutrition_data ADD COLUMN serving_size TEXT")
            print("Added serving_size column to nutrition_data table")

        if 'density' not in nd_columns:
            cursor.execute("ALTER TABLE nutrition_data ADD COLUMN density REAL")
            print("Added density column to nutrition_data table")

        # 更新recipe_ingredients表（如果需要）
        cursor.execute("PRAGMA table_info(recipe_ingredients)")
        ri_columns = [column[1] for column in cursor.fetchall()]

        if 'original_ingredient_text' not in ri_columns:
            cursor.execute("ALTER TABLE recipe_ingredients ADD COLUMN original_ingredient_text TEXT")
            print("Added original_ingredient_text column to recipe_ingredients table")

        if 'required_grade' not in ri_columns:
            cursor.execute("ALTER TABLE recipe_ingredients ADD COLUMN required_grade TEXT")
            print("Added required_grade column to recipe_ingredients table")

        conn.commit()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_database_schema()