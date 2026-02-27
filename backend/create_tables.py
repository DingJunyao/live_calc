#!/usr/bin/env python3
"""
创建数据库表的脚本
"""

import sqlite3
import os
from datetime import datetime


def create_database_tables():
    db_path = "data/livecalc.db"

    # 确保数据目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 创建users表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # 创建invite_codes表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                created_by INTEGER NOT NULL,
                used_count INTEGER DEFAULT 0,
                max_uses INTEGER DEFAULT 1,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # 创建locations表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                latitude REAL,
                longitude REAL,
                user_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建favorite_locations表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorite_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)

        # 创建record_types表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS record_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # 创建product_records表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                location_id INTEGER,
                user_id INTEGER NOT NULL,
                record_type_id INTEGER NOT NULL,
                currency TEXT DEFAULT 'CNY',
                purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (location_id) REFERENCES locations(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (record_type_id) REFERENCES record_types(id)
            )
        """)

        # 创建expenses表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                description TEXT,
                expense_type TEXT,
                user_id INTEGER NOT NULL,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                currency TEXT DEFAULT 'CNY',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建nutrition_data表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nutrition_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usda_food_id TEXT,
                food_name TEXT NOT NULL,
                category TEXT,
                serving_size TEXT,
                energy_kcal REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                fiber_g REAL,
                sugar_g REAL,
                sodium_mg REAL,
                calcium_mg REAL,
                iron_mg REAL,
                vitamin_a_rea_mcg REAL,
                vitamin_c_mg REAL,
                vitamin_d_iu REAL,
                potassium_mg REAL,
                cholesterol_mg REAL,
                saturated_fat_g REAL,
                trans_fat_g REAL,
                monounsaturated_fat_g REAL,
                polyunsaturated_fat_g REAL,
                water_g REAL,
                ash_g REAL,
                thiamin_mg REAL,
                riboflavin_mg REAL,
                niacin_mg REAL,
                pantothenic_acid_mg REAL,
                vitamin_b6_mg REAL,
                biotin_mcg REAL,
                folate_total_mcg REAL,
                folic_acid_mcg REAL,
                food_folate_mcg REAL,
                folate_dfe_mcg REAL,
                choline_total_mg REAL,
                vitamin_b12_mcg REAL,
                vitamin_e_mg REAL,
                vitamin_k_mcg REAL,
                beta_carotene_mcg REAL,
                alpha_carotene_mcg REAL,
                cryptoxanthin_mcg REAL,
                lycopene_mcg REAL,
                lut_and_zeax_mcg REAL,
                retinol_mcg REAL,
                carotene_beta_mcg REAL,
                carotene_alpha_mcg REAL,
                vitamin_e_added_mg REAL,
                vitamin_b12_added_mcg REAL,
                cholesterol_choline_mg REAL,
                tryptophan_g REAL,
                valine_g REAL,
                threonine_g REAL,
                isoleucine_g REAL,
                leucine_g REAL,
                lysine_g REAL,
                methionine_g REAL,
                cystine_g REAL,
                phenylalanine_g REAL,
                tyrosine_g REAL,
                arginine_g REAL,
                histidine_g REAL,
                alanine_g REAL,
                aspartic_acid_g REAL,
                glutamic_acid_g REAL,
                glycine_g REAL,
                proline_g REAL,
                serine_g REAL,
                hydroxyproline_g REAL,
                caffeine_mg REAL,
                theobromine_mg REAL,
                alcohol_g REAL,
                nutrients TEXT, -- JSON格式存储额外营养信息
                density REAL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # 创建ingredients表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category_id INTEGER,
                density REAL,
                default_unit TEXT,
                name_variants TEXT, -- JSON格式存储名称变体
                nutrition_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (category_id) REFERENCES ingredient_categories(id),
                FOREIGN KEY (nutrition_id) REFERENCES nutrition_data(id)
            )
        """)

        # 创建ingredient_nutrition_mapping表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_nutrition_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_id INTEGER NOT NULL,
                nutrition_data_id INTEGER NOT NULL,
                ratio REAL DEFAULT 1.0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
                FOREIGN KEY (nutrition_data_id) REFERENCES nutrition_data(id)
            )
        """)

        # 创建ingredient_categories表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                display_name TEXT,
                parent_category_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (parent_category_id) REFERENCES ingredient_categories(id)
            )
        """)

        # 创建units表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                abbreviation TEXT NOT NULL,
                plural_form TEXT,
                unit_type TEXT NOT NULL, -- mass, volume, length, etc.
                si_factor REAL, -- 转换为国际单位制的系数
                is_si_base BOOLEAN DEFAULT 0,
                is_common BOOLEAN DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # 创建unit_conversions表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unit_conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_unit_id INTEGER NOT NULL,
                to_unit_id INTEGER NOT NULL,
                factor REAL NOT NULL, -- 转换系数
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (from_unit_id) REFERENCES units(id),
                FOREIGN KEY (to_unit_id) REFERENCES units(id)
            )
        """)

        # 创建region_unit_settings表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS region_unit_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_name TEXT NOT NULL,
                default_mass_unit TEXT,
                default_volume_unit TEXT,
                default_length_unit TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # 创建user_unit_preferences表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_unit_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                preferred_mass_unit TEXT,
                preferred_volume_unit TEXT,
                preferred_length_unit TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建ingredient_densities表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_densities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL,
                density REAL NOT NULL, -- 密度(g/ml)
                unit TEXT DEFAULT 'g/ml',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # 创建ingredient_hierarchy表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_hierarchy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,  -- 父级食材
                child_id INTEGER,   -- 子级食材
                relationship_type TEXT,  -- 包含关系、替代关系等
                confidence REAL DEFAULT 1.00,  -- 关系置信度
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (parent_id) REFERENCES ingredients(id),
                FOREIGN KEY (child_id) REFERENCES ingredients(id)
            )
        """)

        # 创建product_ingredient_links表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_ingredient_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_record_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity REAL,
                unit TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (product_record_id) REFERENCES product_records(id),
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
            )
        """)

        # 创建recipes表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT,
                user_id INTEGER,
                tags TEXT, -- JSON格式存储标签
                cooking_steps TEXT, -- JSON格式存储烹饪步骤
                total_time_minutes INTEGER,
                difficulty TEXT,
                servings INTEGER DEFAULT 1,
                tips TEXT, -- JSON格式存储提示
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 创建recipe_ingredients表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity TEXT NOT NULL,
                unit TEXT,
                original_ingredient_text TEXT,
                required_grade TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id),
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
            )
        """)

        conn.commit()
        print("所有数据库表创建成功！")

    except Exception as e:
        print(f"创建数据库表时出错: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    create_database_tables()