# -*- coding: utf-8 -*-
"""执行数据迁移"""
import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("d:/code/live_calc")
OLD_DB = PROJECT_ROOT / "backend" / "data" / "livecalc_bak.db"
NEW_DB = PROJECT_ROOT / "backend" / "data" / "livecalc.db"

# 备份
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = NEW_DB.with_name(f"livecalc_pre_migration_{timestamp}.db")
shutil.copy2(NEW_DB, backup_path)
print(f"Backup: {backup_path}")

old_conn = sqlite3.connect(str(OLD_DB))
new_conn = sqlite3.connect(str(NEW_DB))

try:
    # 1. 迁移用户
    print("--- Step 1: User ---")
    old_user = old_conn.execute("SELECT * FROM users LIMIT 1").fetchone()
    cols = [desc[0] for desc in new_conn.execute("SELECT * FROM users LIMIT 0").description]
    user_data = {
        "username": old_user[1],
        "email": old_user[2],
        "phone": old_user[3],
        "password_hash": old_user[4],
        "is_admin": old_user[5],
        "is_active": old_user[6],
        "email_verified": old_user[7],
        "created_at": old_user[8],
        "updated_at": old_user[9],
    }
    insert_cols = [c for c in user_data.keys() if c in cols]
    insert_vals = [user_data[c] for c in insert_cols]
    placeholders = ", ".join(["?"] * len(insert_cols))
    col_str = ", ".join(insert_cols)
    new_conn.execute(
        f"INSERT INTO users ({col_str}) VALUES ({placeholders})", insert_vals
    )
    new_user_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"User migrated: {old_user[1]} (new_id={new_user_id})")

    # 2. 迁移商家
    print("--- Step 2: Merchants ---")
    merchant_id_mapping = {}
    m_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM merchants LIMIT 0").description]
    for row in old_conn.execute(
        "SELECT id, name, address, latitude, longitude, created_at, updated_at "
        "FROM merchants WHERE is_active = 1"
    ).fetchall():
        m_data = {
            "user_id": new_user_id,
            "name": row[1],
            "address": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "created_at": row[5],
            "updated_at": row[6],
        }
        ic = [c for c in m_data.keys() if c in m_cols]
        iv = [m_data[c] for c in ic]
        new_conn.execute(
            f"INSERT INTO merchants ({', '.join(ic)}) VALUES ({', '.join(['?'] * len(ic))})",
            iv,
        )
        new_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        merchant_id_mapping[row[0]] = new_id
        print(f"  Merchant: {row[1]} ({row[0]} -> {new_id})")

    # 3. 构建查找表
    ingredient_lookup = {}
    for r in new_conn.execute(
        "SELECT id, name, aliases FROM ingredients WHERE is_active = 1"
    ).fetchall():
        ingredient_lookup[r[1]] = r[0]
        if r[2]:
            for a in json.loads(r[2]):
                ingredient_lookup[a] = r[0]

    new_product_lookup = {}
    for r in new_conn.execute(
        "SELECT id, name FROM products WHERE is_active = 1"
    ).fetchall():
        new_product_lookup[r[1]] = r[0]

    prod_by_ing = {}
    for r in new_conn.execute(
        "SELECT ingredient_id, MIN(id) FROM products WHERE is_active = 1 GROUP BY ingredient_id"
    ).fetchall():
        prod_by_ing[r[0]] = r[1]

    # 获取旧库有价格记录的商品
    products_with_records = {}
    for row in old_conn.execute(
        "SELECT DISTINCT p.id, p.name, p.brand, p.barcode, p.ingredient_id, "
        "p.image_url, p.tags "
        "FROM products p INNER JOIN product_records pr ON pr.product_id = p.id "
        "WHERE p.is_active = 1 AND pr.is_active = 1"
    ).fetchall():
        products_with_records[row[0]] = {
            "name": row[1],
            "brand": row[2],
            "barcode": row[3],
            "ingredient_id": row[4],
            "image_url": row[5],
            "tags": row[6],
        }

    # 4. 映射商品
    print("--- Step 3: Product mapping ---")
    product_id_mapping = {}
    new_products_created = 0

    for old_id, pinfo in products_with_records.items():
        name = pinfo["name"]
        # 直接匹配商品
        if name in new_product_lookup:
            product_id_mapping[old_id] = new_product_lookup[name]
            continue
        # 通过原料匹配
        if name in ingredient_lookup:
            ing_id = ingredient_lookup[name]
            if ing_id in prod_by_ing:
                product_id_mapping[old_id] = prod_by_ing[ing_id]
                continue

        # 未匹配 - 创建新的
        ing_id = ingredient_lookup.get(name)
        if not ing_id:
            default_cat = new_conn.execute(
                "SELECT id FROM ingredient_categories WHERE is_active = 1 LIMIT 1"
            ).fetchone()[0]
            new_conn.execute(
                "INSERT INTO ingredients (name, category_id, is_imported, is_merged, "
                "created_at, updated_at, is_active) "
                "VALUES (?, ?, 0, 0, datetime('now'), datetime('now'), 1)",
                (name, default_cat),
            )
            ing_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            ingredient_lookup[name] = ing_id
            print(f"  New ingredient: {name} (id={ing_id})")

        new_conn.execute(
            "INSERT INTO products (name, brand, barcode, image_url, ingredient_id, tags, "
            "created_at, updated_at, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1)",
            (name, pinfo["brand"], pinfo["barcode"], pinfo["image_url"], ing_id, pinfo["tags"]),
        )
        new_prod_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        product_id_mapping[old_id] = new_prod_id
        new_product_lookup[name] = new_prod_id
        new_products_created += 1
        print(f"  New product: {name} ({old_id} -> {new_prod_id})")

    print(f"  Mapped: {len(product_id_mapping)}, Created: {new_products_created}")

    # 5. 迁移价格记录
    print("--- Step 4: Price records ---")
    record_cols = [
        desc[0]
        for desc in new_conn.execute("SELECT * FROM product_records LIMIT 0").description
    ]
    records_migrated = 0
    records_skipped = 0

    for row in old_conn.execute(
        "SELECT id, user_id, product_id, product_name, merchant_id, price, currency, "
        "original_quantity, original_unit_id, standard_quantity, standard_unit_id, "
        "record_type, exchange_rate, recorded_at, notes "
        "FROM product_records WHERE is_active = 1 ORDER BY id"
    ).fetchall():
        new_prod_id = product_id_mapping.get(row[2])
        if not new_prod_id:
            new_prod_id = new_product_lookup.get(row[3])
            if not new_prod_id:
                records_skipped += 1
                continue

        new_merchant_id = merchant_id_mapping.get(row[4]) if row[4] else None

        r_data = {
            "user_id": new_user_id,
            "product_id": new_prod_id,
            "product_name": row[3],
            "merchant_id": new_merchant_id,
            "price": row[5],
            "currency": row[6],
            "original_quantity": row[7],
            "original_unit_id": row[8],
            "standard_quantity": row[9],
            "standard_unit_id": row[10],
            "record_type": row[11],
            "exchange_rate": row[12],
            "recorded_at": row[13],
            "notes": row[14],
        }
        ic = [c for c in r_data.keys() if c in record_cols]
        iv = [r_data[c] for c in ic]
        new_conn.execute(
            f"INSERT INTO product_records ({', '.join(ic)}) VALUES ({', '.join(['?'] * len(ic))})",
            iv,
        )
        records_migrated += 1

    print(f"  Records: {records_migrated} migrated, {records_skipped} skipped")

    new_conn.commit()
    print("\nMigration committed!")

    # 验证
    print("\n--- Verification ---")
    for table in ["users", "merchants", "products", "product_records"]:
        count = new_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count}")

    # 保存映射关系供SQL生成使用
    import json

    mapping = {
        "new_user_id": new_user_id,
        "merchant_id_mapping": merchant_id_mapping,
        "product_id_mapping": product_id_mapping,
        "records_migrated": records_migrated,
        "records_skipped": records_skipped,
        "new_products_created": new_products_created,
    }
    with open(PROJECT_ROOT / "backend" / "scripts" / "migration_mapping.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nMapping saved to migration_mapping.json")

except Exception as e:
    new_conn.rollback()
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    old_conn.close()
    new_conn.close()
