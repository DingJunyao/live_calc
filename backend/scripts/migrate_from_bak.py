# -*- coding: utf-8 -*-
"""
数据迁移脚本：从旧版本数据库迁移到新版本数据库

迁移内容：
1. 用户 (users)
2. 商家 (merchants)
3. 新商品 (products) - 仅迁移新库中不存在的商品
4. 价格记录 (product_records)

使用方法：
    cd backend
    python scripts/migrate_from_bak.py

注意：
    - 执行前会自动备份新数据库
    - 单位 ID 在 product_records 使用的范围内（2-18）完全一致，无需映射
"""

import sqlite3
import json
import shutil
import os
import sys
from datetime import datetime
from pathlib import Path

# 数据库路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OLD_DB = PROJECT_ROOT / "backend" / "data" / "livecalc_bak.db"
NEW_DB = PROJECT_ROOT / "backend" / "data" / "livecalc.db"
SQL_OUTPUT = PROJECT_ROOT / "backend" / "scripts" / "migration_data.sql"


def backup_database(db_path: Path) -> Path:
    """备份数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"livecalc_pre_migration_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    print(f"✅ 数据库已备份到: {backup_path}")
    return backup_path


def build_ingredient_lookup(new_conn: sqlite3.Connection) -> dict:
    """构建新库原料查找表：{名称/别名: ingredient_id}"""
    lookup = {}
    for row in new_conn.execute(
        "SELECT id, name, aliases FROM ingredients WHERE is_active = 1"
    ).fetchall():
        ing_id, name, aliases_json = row
        lookup[name] = ing_id
        if aliases_json:
            for alias in json.loads(aliases_json):
                lookup[alias] = ing_id
    return lookup


def build_product_lookup(new_conn: sqlite3.Connection) -> dict:
    """构建新库商品查找表：{名称: product_id}"""
    lookup = {}
    for row in new_conn.execute(
        "SELECT id, name FROM products WHERE is_active = 1"
    ).fetchall():
        lookup[row[1]] = row[0]
    return lookup


def build_product_by_ingredient_lookup(new_conn: sqlite3.Connection) -> dict:
    """构建 ingredient_id -> product_id 的映射（每个原料取第一个商品）"""
    lookup = {}
    for row in new_conn.execute(
        "SELECT ingredient_id, MIN(id) FROM products WHERE is_active = 1 GROUP BY ingredient_id"
    ).fetchall():
        lookup[row[0]] = row[1]
    return lookup


def build_unit_name_map(conn: sqlite3.Connection) -> dict:
    """构建 unit_id -> unit_name 的映射"""
    return {r[0]: r[1] for r in conn.execute("SELECT id, name FROM units").fetchall()}


def build_unit_id_by_name(conn: sqlite3.Connection) -> dict:
    """构建 unit_name -> unit_id 的映射"""
    return {r[1]: r[0] for r in conn.execute("SELECT id, name FROM units").fetchall()}


def find_matching_product(
    old_product_name: str,
    new_product_lookup: dict,
    ingredient_lookup: dict,
    product_by_ingredient: dict,
) -> tuple:
    """
    查找旧商品在新库中的对应商品。
    返回 (new_product_id, match_method) 或 (None, None)
    match_method: 'product_name' | 'ingredient_name' | 'ingredient_alias' | None
    """
    # 1. 直接匹配商品名称
    if old_product_name in new_product_lookup:
        return new_product_lookup[old_product_name], "product_name"

    # 2. 匹配原料名称/别名
    if old_product_name in ingredient_lookup:
        ing_id = ingredient_lookup[old_product_name]
        if ing_id in product_by_ingredient:
            return product_by_ingredient[ing_id], "ingredient_match"

    return None, None


def migrate_user(old_conn: sqlite3.Connection, new_conn: sqlite3.Connection) -> int:
    """迁移用户，返回新库中的 user_id"""
    old_user = old_conn.execute("SELECT * FROM users LIMIT 1").fetchone()
    if not old_user:
        print("⚠️  旧库无用户数据")
        return None

    old_id = old_user[0]
    username = old_user[1]
    email = old_user[2]

    # 检查新库是否已有该用户
    existing = new_conn.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()

    if existing:
        print(f"  用户 '{username}' 已存在 (id={existing[0]})")
        return existing[0]

    # 新库 users 表结构可能略有不同，插入时指定列名
    cols = [desc[0] for desc in new_conn.execute("SELECT * FROM users LIMIT 0").description]

    # 构建插入数据
    user_data = {
        "username": username,
        "email": email,
        "phone": old_user[3],
        "password_hash": old_user[4],
        "is_admin": old_user[5],
        "is_active": old_user[6],
        "email_verified": old_user[7],
        "created_at": old_user[8],
        "updated_at": old_user[9],
    }

    # 只插入新库表存在的字段
    insert_cols = [c for c in user_data.keys() if c in cols]
    insert_vals = [user_data[c] for c in insert_cols]

    placeholders = ", ".join(["?"] * len(insert_cols))
    col_names = ", ".join(insert_cols)
    new_conn.execute(
        f"INSERT INTO users ({col_names}) VALUES ({placeholders})", insert_vals
    )
    new_user_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"  用户 '{username}' 已迁移 (old_id={old_id} -> new_id={new_user_id})")
    return new_user_id


def migrate_merchants(
    old_conn: sqlite3.Connection, new_conn: sqlite3.Connection, new_user_id: int
) -> dict:
    """迁移商家，返回 {old_merchant_id: new_merchant_id} 映射"""
    id_mapping = {}
    count = 0

    # 获取新库 merchants 表列
    cols = [desc[0] for desc in new_conn.execute("SELECT * FROM merchants LIMIT 0").description]

    for row in old_conn.execute(
        "SELECT id, user_id, name, address, latitude, longitude, created_at, updated_at, "
        "created_by, updated_by, is_active FROM merchants WHERE is_active = 1"
    ).fetchall():
        old_id = row[0]
        merchant_data = {
            "user_id": new_user_id,
            "name": row[2],
            "address": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "created_at": row[6],
            "updated_at": row[7],
            "created_by": new_user_id if "created_by" in cols else None,
            "updated_by": new_user_id if "updated_by" in cols else None,
            "is_active": 1 if "is_active" in cols else None,
        }

        insert_cols = [c for c in merchant_data.keys() if c in cols and merchant_data[c] is not None]
        insert_vals = [merchant_data[c] for c in insert_cols]

        placeholders = ", ".join(["?"] * len(insert_cols))
        col_names = ", ".join(insert_cols)
        new_conn.execute(
            f"INSERT INTO merchants ({col_names}) VALUES ({placeholders})", insert_vals
        )
        new_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        id_mapping[old_id] = new_id
        count += 1
        print(f"  商家 '{row[2]}' (old_id={old_id} -> new_id={new_id})")

    print(f"✅ 迁移商家: {count} 条")
    return id_mapping


def migrate_products_and_records(
    old_conn: sqlite3.Connection,
    new_conn: sqlite3.Connection,
    new_user_id: int,
    merchant_id_mapping: dict,
) -> dict:
    """
    迁移商品（仅新建的）和价格记录。
    返回迁移统计信息。
    """
    # 构建查找表
    ingredient_lookup = build_ingredient_lookup(new_conn)
    new_product_lookup = build_product_lookup(new_conn)
    product_by_ingredient = build_product_by_ingredient_lookup(new_conn)

    # 获取新库表列
    prod_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM products LIMIT 0").description]
    record_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM product_records LIMIT 0").description]

    # 获取旧库中有价格记录的商品
    products_with_records = {}
    for row in old_conn.execute(
        "SELECT DISTINCT p.id, p.name, p.brand, p.barcode, p.ingredient_id, "
        "p.image_url, p.tags, p.custom_nutrition_data, p.custom_nutrition_source "
        "FROM products p "
        "INNER JOIN product_records pr ON pr.product_id = p.id "
        "WHERE p.is_active = 1 AND pr.is_active = 1"
    ).fetchall():
        products_with_records[row[0]] = {
            "id": row[0],
            "name": row[1],
            "brand": row[2],
            "barcode": row[3],
            "ingredient_id": row[4],
            "image_url": row[5],
            "tags": row[6],
            "custom_nutrition_data": row[7],
            "custom_nutrition_source": row[8],
        }

    # 也获取没有价格记录但需要迁移的商品（如果用户要求）
    # 这里先只处理有价格记录的

    # 建立旧商品ID -> 新商品ID的映射
    product_id_mapping = {}
    unmatched_products = {}
    new_products_created = 0

    for old_prod_id, prod_info in products_with_records.items():
        new_prod_id, match_method = find_matching_product(
            prod_info["name"], new_product_lookup, ingredient_lookup, product_by_ingredient
        )

        if new_prod_id:
            product_id_mapping[old_prod_id] = new_prod_id
            continue

        # 未找到匹配，需要在 new_ingredients 和 new_products 中创建
        # 先尝试找对应的 ingredient_id
        ing_id = ingredient_lookup.get(prod_info["name"])

        if not ing_id:
            # 需要创建新的 ingredient
            # 使用默认分类（id=1 或第一个分类）
            default_category = new_conn.execute(
                "SELECT id FROM ingredient_categories WHERE is_active = 1 LIMIT 1"
            ).fetchone()[0]

            new_conn.execute(
                "INSERT INTO ingredients (name, category_id, is_imported, is_merged, created_at, updated_at, is_active) "
                "VALUES (?, ?, 0, 0, datetime('now'), datetime('now'), 1)",
                (prod_info["name"], default_category),
            )
            ing_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            # 更新查找表
            ingredient_lookup[prod_info["name"]] = ing_id
            print(f"    新建原料: '{prod_info['name']}' (id={ing_id})")

        # 创建新商品
        new_conn.execute(
            "INSERT INTO products (name, brand, barcode, image_url, ingredient_id, tags, "
            "custom_nutrition_data, custom_nutrition_source, created_at, updated_at, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1)",
            (
                prod_info["name"],
                prod_info["brand"],
                prod_info["barcode"],
                prod_info["image_url"],
                ing_id,
                prod_info["tags"],
                prod_info["custom_nutrition_data"],
                prod_info["custom_nutrition_source"],
            ),
        )
        new_prod_id = new_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        product_id_mapping[old_prod_id] = new_prod_id
        new_product_lookup[prod_info["name"]] = new_prod_id
        new_products_created += 1
        print(f"    新建商品: '{prod_info['name']}' (old_id={old_prod_id} -> new_id={new_prod_id})")

    print(f"  商品映射: {len(product_id_mapping)} 个（新建 {new_products_created} 个）")

    # 迁移价格记录
    records_migrated = 0
    records_skipped = 0

    for row in old_conn.execute(
        "SELECT id, user_id, product_id, product_name, merchant_id, price, currency, "
        "original_quantity, original_unit_id, standard_quantity, standard_unit_id, "
        "record_type, exchange_rate, recorded_at, notes "
        "FROM product_records WHERE is_active = 1 "
        "ORDER BY id"
    ).fetchall():
        old_product_id = row[2]
        old_merchant_id = row[4]

        # 检查商品映射
        new_product_id = product_id_mapping.get(old_product_id)
        if not new_product_id:
            # 尝试通过 product_name 直接匹配
            new_product_id = new_product_lookup.get(row[3])
            if not new_product_id:
                records_skipped += 1
                continue

        # 处理商家映射
        new_merchant_id = merchant_id_mapping.get(old_merchant_id) if old_merchant_id else None

        # 构建插入数据
        record_data = {
            "user_id": new_user_id,
            "product_id": new_product_id,
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

        insert_cols = [c for c in record_data.keys() if c in record_cols]
        insert_vals = [record_data[c] for c in insert_cols]

        placeholders = ", ".join(["?"] * len(insert_cols))
        col_names = ", ".join(insert_cols)
        new_conn.execute(
            f"INSERT INTO product_records ({col_names}) VALUES ({placeholders})", insert_vals
        )
        records_migrated += 1

    print(f"✅ 价格记录迁移完成: {records_migrated} 条成功, {records_skipped} 条跳过")

    return {
        "products_mapped": len(product_id_mapping),
        "products_created": new_products_created,
        "records_migrated": records_migrated,
        "records_skipped": records_skipped,
    }


def generate_sql_script(
    old_conn: sqlite3.Connection,
    new_conn: sqlite3.Connection,
    new_user_id: int,
    merchant_id_mapping: dict,
    stats: dict,
) -> str:
    """生成可移植的 SQL 脚本"""
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- 数据迁移 SQL 脚本")
    lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("-- 源: livecalc_bak.db (旧版本)")
    lines.append("-- 目标: livecalc.db (新版本)")
    lines.append("-- ============================================================")
    lines.append("")

    # 重建查找表
    ingredient_lookup = build_ingredient_lookup(new_conn)
    new_product_lookup = build_product_lookup(new_conn)
    product_by_ingredient = build_product_by_ingredient_lookup(new_conn)

    # 获取新库表列
    user_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM users LIMIT 0").description]
    merchant_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM merchants LIMIT 0").description]
    prod_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM products LIMIT 0").description]
    record_cols = [desc[0] for desc in new_conn.execute("SELECT * FROM product_records LIMIT 0").description]

    # 用户
    lines.append("-- ============================================================")
    lines.append("-- 1. 用户迁移")
    lines.append("-- ============================================================")
    old_user = old_conn.execute("SELECT * FROM users LIMIT 1").fetchone()
    if old_user:
        user_data = {
            "username": old_user[1],
            "email": old_user[2],
            "phone": _sql_val(old_user[3]),
            "password_hash": _sql_val(old_user[4]),
            "is_admin": _sql_val(old_user[5]),
            "is_active": _sql_val(old_user[6]),
            "email_verified": _sql_val(old_user[7]),
            "created_at": _sql_val(old_user[8]),
            "updated_at": _sql_val(old_user[9]),
        }
        insert_cols = [c for c in user_data.keys() if c in user_cols]
        col_str = ", ".join(insert_cols)
        val_str = ", ".join([str(user_data[c]) for c in insert_cols])
        lines.append(f"INSERT INTO users ({col_str}) VALUES ({val_str});")
        lines.append(f"-- 新用户 ID = {new_user_id}")
    lines.append("")

    # 商家
    lines.append("-- ============================================================")
    lines.append("-- 2. 商家迁移")
    lines.append("-- ============================================================")
    for row in old_conn.execute(
        "SELECT id, name, address, latitude, longitude, created_at, updated_at "
        "FROM merchants WHERE is_active = 1"
    ).fetchall():
        old_id = row[0]
        new_id = merchant_id_mapping.get(old_id)
        m_data = {
            "user_id": new_user_id,
            "name": _sql_val(row[1]),
            "address": _sql_val(row[2]),
            "latitude": _sql_val(row[3]),
            "longitude": _sql_val(row[4]),
            "created_at": _sql_val(row[5]),
            "updated_at": _sql_val(row[6]),
        }
        insert_cols = [c for c in m_data.keys() if c in merchant_cols]
        col_str = ", ".join(insert_cols)
        val_str = ", ".join([str(m_data[c]) for c in insert_cols])
        lines.append(f"-- 旧ID={old_id} -> 新ID={new_id}")
        lines.append(f"INSERT INTO merchants ({col_str}) VALUES ({val_str});")
    lines.append("")

    # 商品（仅新建的）
    lines.append("-- ============================================================")
    lines.append("-- 3. 新商品迁移（旧库有价格记录但新库不存在的商品）")
    lines.append("-- ============================================================")
    lines.append("-- 注意：需要先确保对应原料存在，如果没有则需要创建")
    lines.append("")

    # 收集需要新建的商品
    products_with_records = {}
    for row in old_conn.execute(
        "SELECT DISTINCT p.id, p.name, p.brand, p.barcode, p.ingredient_id, "
        "p.image_url, p.tags FROM products p "
        "INNER JOIN product_records pr ON pr.product_id = p.id "
        "WHERE p.is_active = 1 AND pr.is_active = 1"
    ).fetchall():
        products_with_records[row[0]] = {
            "name": row[1], "brand": row[2], "barcode": row[3],
            "ingredient_id": row[4], "image_url": row[5], "tags": row[6],
        }

    new_product_sql_list = []
    for old_prod_id, prod_info in products_with_records.items():
        new_prod_id, _ = find_matching_product(
            prod_info["name"], new_product_lookup, ingredient_lookup, product_by_ingredient
        )
        if not new_prod_id:
            new_product_sql_list.append((old_prod_id, prod_info))

    if new_product_sql_list:
        for old_prod_id, prod_info in new_product_sql_list:
            ing_id = ingredient_lookup.get(prod_info["name"])
            if not ing_id:
                lines.append(f"-- 需要先创建原料: {prod_info['name']}")
                lines.append(f"INSERT INTO ingredients (name, category_id, is_imported, is_merged, created_at, updated_at, is_active)")
                lines.append(f"VALUES ('{_escape_sql(prod_info['name'])}', 1, 0, 0, datetime('now'), datetime('now'), 1);")
                lines.append(f"SET @new_ing_id = LAST_INSERT_ID(); -- MySQL")
                lines.append(f"-- SQLite: 需要手动获取新ID")
                lines.append("")

            ing_id_val = f"'{ing_id}'" if ing_id else "@new_ing_id"
            p_data = {
                "name": _sql_val(prod_info["name"]),
                "brand": _sql_val(prod_info.get("brand")),
                "barcode": _sql_val(prod_info.get("barcode")),
                "image_url": _sql_val(prod_info.get("image_url")),
                "ingredient_id": ing_id_val,
                "tags": _sql_val(prod_info.get("tags")),
                "is_active": 1,
            }
            insert_cols = [c for c in p_data.keys() if c in prod_cols]
            col_str = ", ".join(insert_cols)
            val_str = ", ".join([str(p_data[c]) for c in insert_cols])
            lines.append(f"-- 商品: {prod_info['name']} (旧ID={old_prod_id})")
            lines.append(f"INSERT INTO products ({col_str}) VALUES ({val_str});")
            lines.append("")

    # 价格记录
    lines.append("-- ============================================================")
    lines.append("-- 4. 价格记录迁移")
    lines.append("-- ============================================================")
    lines.append("-- 注意：product_id 和 merchant_id 需要替换为新库中的ID")
    lines.append("-- 以下 SQL 中的 {NEW_PRODUCT_ID} 和 {NEW_MERCHANT_ID} 为占位符")
    lines.append("-- 实际执行时需要根据映射关系替换")
    lines.append("")

    # 为了生成准确的SQL，重建完整的映射
    product_id_mapping = {}
    for old_prod_id, prod_info in products_with_records.items():
        new_prod_id, _ = find_matching_product(
            prod_info["name"], new_product_lookup, ingredient_lookup, product_by_ingredient
        )
        if new_prod_id:
            product_id_mapping[old_prod_id] = new_prod_id

    record_count = 0
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
                continue

        new_merchant_id = merchant_id_mapping.get(row[4]) if row[4] else "NULL"

        r_data = {
            "user_id": new_user_id,
            "product_id": new_prod_id,
            "product_name": _sql_val(row[3]),
            "merchant_id": new_merchant_id,
            "price": _sql_val(row[5]),
            "currency": _sql_val(row[6]),
            "original_quantity": _sql_val(row[7]),
            "original_unit_id": _sql_val(row[8]),
            "standard_quantity": _sql_val(row[9]),
            "standard_unit_id": _sql_val(row[10]),
            "record_type": _sql_val(row[11]),
            "exchange_rate": _sql_val(row[12]),
            "recorded_at": _sql_val(row[13]),
            "notes": _sql_val(row[14]),
        }
        insert_cols = [c for c in r_data.keys() if c in record_cols]
        col_str = ", ".join(insert_cols)
        val_str = ", ".join([str(r_data[c]) for c in insert_cols])
        lines.append(f"INSERT INTO product_records ({col_str}) VALUES ({val_str});")
        record_count += 1

    lines.append("")
    lines.append(f"-- 共 {record_count} 条价格记录")
    lines.append("")
    lines.append("-- ============================================================")
    lines.append("-- 迁移统计")
    lines.append("-- ============================================================")
    lines.append(f"-- 商家: {len(merchant_id_mapping)} 条")
    lines.append(f"-- 新建商品: {stats.get('products_created', 0)} 个")
    lines.append(f"-- 价格记录: {stats.get('records_migrated', 0)} 条成功, {stats.get('records_skipped', 0)} 条跳过")
    lines.append(f"-- 总计 SQL 语句: {len([l for l in lines if l.startswith('INSERT')])} 条")

    return "\n".join(lines)


def _sql_val(val) -> str:
    """将 Python 值转为 SQL 值"""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    return f"'{_escape_sql(str(val))}'"


def _escape_sql(val: str) -> str:
    """转义 SQL 字符串"""
    return val.replace("'", "''")


def main():
    print("=" * 60)
    print("数据迁移：livecalc_bak.db -> livecalc.db")
    print("=" * 60)

    # 验证文件存在
    if not OLD_DB.exists():
        print(f"❌ 旧数据库不存在: {OLD_DB}")
        sys.exit(1)
    if not NEW_DB.exists():
        print(f"❌ 新数据库不存在: {NEW_DB}")
        sys.exit(1)

    # 确认执行
    print(f"\n旧数据库: {OLD_DB}")
    print(f"新数据库: {NEW_DB}")
    print(f"SQL 输出: {SQL_OUTPUT}")
    response = input("\n⚠️  确认执行迁移？(yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        sys.exit(0)

    # 备份
    backup_database(NEW_DB)

    # 连接数据库
    old_conn = sqlite3.connect(str(OLD_DB))
    new_conn = sqlite3.connect(str(NEW_DB))

    try:
        # 1. 迁移用户
        print("\n--- 步骤 1: 迁移用户 ---")
        new_user_id = migrate_user(old_conn, new_conn)
        if not new_user_id:
            print("❌ 无法迁移用户，终止")
            sys.exit(1)

        # 2. 迁移商家
        print("\n--- 步骤 2: 迁移商家 ---")
        merchant_id_mapping = migrate_merchants(old_conn, new_conn, new_user_id)

        # 3. 迁移商品和价格记录
        print("\n--- 步骤 3: 迁移商品和价格记录 ---")
        stats = migrate_products_and_records(
            old_conn, new_conn, new_user_id, merchant_id_mapping
        )

        # 4. 生成 SQL 脚本
        print("\n--- 步骤 4: 生成 SQL 脚本 ---")
        sql_content = generate_sql_script(
            old_conn, new_conn, new_user_id, merchant_id_mapping, stats
        )
        os.makedirs(SQL_OUTPUT.parent, exist_ok=True)
        with open(SQL_OUTPUT, "w", encoding="utf-8") as f:
            f.write(sql_content)
        print(f"✅ SQL 脚本已生成: {SQL_OUTPUT}")

        # 提交事务
        new_conn.commit()
        print("\n✅ 迁移完成！所有数据已提交。")

        # 验证
        print("\n--- 验证 ---")
        for table in ["users", "merchants", "products", "product_records"]:
            count = new_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} 条记录")

    except Exception as e:
        new_conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        print("已回滚所有更改。")
        raise
    finally:
        old_conn.close()
        new_conn.close()


if __name__ == "__main__":
    main()
