#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 livecalc_bak.db 向 livecalc.db 迁移数据。

迁移内容：
1. 商家（merchants）—— 按名称匹配，新增不存在的商家
2. 食材（ingredients）—— 按名称匹配，新增不存在的食材
3. 商品（products）—— 按名称匹配，新增不存在的商品
4. 价格记录（product_records）—— 按商品名映射 product_id，按商家名映射 merchant_id
5. 食材层级关系（ingredient_hierarchies）—— 按食材名映射 parent_id / child_id
6. 实体单位覆盖（entity_unit_overrides）—— 按 entity_type + 名称 + unit_name 映射

不修改已有数据，仅做追加。不改动默认单位、食材分类、菜谱类型。
"""

import sqlite3
import sys
from pathlib import Path

BAK_PATH = Path(__file__).parent.parent / "data" / "livecalc_bak.db"
NEW_PATH = Path(__file__).parent.parent / "data" / "livecalc.db"


def log(msg: str):
    print(f"  ✓ {msg}")


def warn(msg: str):
    print(f"  ⚠ {msg}")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def main():
    if not BAK_PATH.exists():
        print(f"❌ 找不到备份数据库: {BAK_PATH}")
        sys.exit(1)
    if not NEW_PATH.exists():
        print(f"❌ 找不到目标数据库: {NEW_PATH}")
        sys.exit(1)

    bak = connect(BAK_PATH)
    new = connect(NEW_PATH)

    # =========================================================
    # 1. 迁移商家
    # =========================================================
    print("\n=== 1. 迁移商家 ===")
    new_merchant_names = {r["name"] for r in new.execute("SELECT name FROM merchants")}
    bak_merchants = bak.execute("SELECT * FROM merchants").fetchall()
    merchant_name_to_new_id = {}

    for m in bak_merchants:
        if m["name"] in new_merchant_names:
            existing = new.execute(
                "SELECT id FROM merchants WHERE name = ?", (m["name"],)
            ).fetchone()
            merchant_name_to_new_id[m["name"]] = existing["id"]
            continue

        new.execute(
            """INSERT INTO merchants (user_id, name, address, latitude, longitude, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (1, m["name"], m["address"], m["latitude"], m["longitude"],
             m["created_at"], m["updated_at"]),
        )
        merchant_name_to_new_id[m["name"]] = new.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]
        log(f"商家「{m['name']}」-> new.id={merchant_name_to_new_id[m['name']]}")

    # =========================================================
    # 2. 迁移缺失的食材
    # =========================================================
    print("\n=== 2. 迁移缺失的食材 ===")
    bak_ing = {r["name"]: r for r in bak.execute("SELECT * FROM ingredients").fetchall()}
    new_ing_names = {r["name"] for r in new.execute("SELECT name FROM ingredients").fetchall()}
    ing_name_to_new_id = {r["name"]: r["id"] for r in new.execute("SELECT id, name FROM ingredients").fetchall()}

    missing_ingredients = sorted(set(bak_ing.keys()) - new_ing_names)
    for name in missing_ingredients:
        row = bak_ing[name]
        new.execute(
            """INSERT INTO ingredients
               (name, category_id, density, default_unit_id, aliases,
                nutrition_id, piece_weight, piece_weight_unit_id,
                is_imported, is_merged, merged_into_id,
                created_at, updated_at, created_by, updated_by, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["name"], row["category_id"], row["density"],
             row["default_unit_id"], row["aliases"],
             row["nutrition_id"], row["piece_weight"], row["piece_weight_unit_id"],
             row["is_imported"], row["is_merged"], row["merged_into_id"],
             row["created_at"], row["updated_at"], None, None, 1),
        )
        ing_name_to_new_id[name] = new.execute("SELECT last_insert_rowid()").fetchone()[0]
        log(f"食材「{name}」-> new.id={ing_name_to_new_id[name]}")

    # =========================================================
    # 3. 迁移缺失的商品
    # =========================================================
    print("\n=== 3. 迁移缺失的商品 ===")
    bak_prod = {r["name"]: r for r in bak.execute("SELECT * FROM products").fetchall()}
    new_prod_names = {r["name"] for r in new.execute("SELECT name FROM products").fetchall()}
    prod_name_to_new_id = {r["name"]: r["id"] for r in new.execute("SELECT id, name FROM products").fetchall()}

    missing_products = sorted(set(bak_prod.keys()) - new_prod_names)
    for name in missing_products:
        row = bak_prod[name]
        bak_ing_name = bak.execute(
            "SELECT name FROM ingredients WHERE id = ?", (row["ingredient_id"],)
        ).fetchone()["name"]
        new_ing_id = ing_name_to_new_id.get(bak_ing_name)

        new.execute(
            """INSERT INTO products
               (name, brand, barcode, image_url, ingredient_id, tags,
                custom_nutrition_data, custom_nutrition_source,
                created_at, updated_at, created_by, updated_by, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["name"], row["brand"], row["barcode"], row["image_url"],
             new_ing_id, row["tags"],
             row["custom_nutrition_data"], row["custom_nutrition_source"],
             row["created_at"], row["updated_at"], None, None, 1),
        )
        prod_name_to_new_id[name] = new.execute("SELECT last_insert_rowid()").fetchone()[0]
        log(f"商品「{name}」-> new.id={prod_name_to_new_id[name]}")

    # =========================================================
    # 4. 迁移价格记录
    # =========================================================
    print("\n=== 4. 迁移价格记录 ===")
    bak_records = bak.execute("SELECT * FROM product_records ORDER BY id").fetchall()
    migrated = 0
    skipped = 0

    for rec in bak_records:
        bak_prod_name = bak.execute(
            "SELECT name FROM products WHERE id = ?", (rec["product_id"],)
        ).fetchone()
        if not bak_prod_name:
            warn(f"product_id={rec['product_id']} 在 bak.products 中找不到，跳过")
            skipped += 1
            continue
        new_prod_id = prod_name_to_new_id.get(bak_prod_name["name"])
        if not new_prod_id:
            warn(f"商品「{bak_prod_name['name']}」在 new.products 中找不到，跳过")
            skipped += 1
            continue

        new_merchant_id = None
        if rec["merchant_id"] is not None:
            bak_merchant_name = bak.execute(
                "SELECT name FROM merchants WHERE id = ?", (rec["merchant_id"],)
            ).fetchone()
            if bak_merchant_name:
                new_merchant_id = merchant_name_to_new_id.get(bak_merchant_name["name"])

        new.execute(
            """INSERT INTO product_records
               (user_id, product_id, product_name, merchant_id,
                price, currency, original_quantity, original_unit_id,
                standard_quantity, standard_unit_id, record_type,
                exchange_rate, recorded_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rec["user_id"], new_prod_id, rec["product_name"] or bak_prod_name["name"],
             new_merchant_id, rec["price"], rec["currency"],
             rec["original_quantity"], rec["original_unit_id"],
             rec["standard_quantity"], rec["standard_unit_id"],
             rec["record_type"], rec["exchange_rate"],
             rec["recorded_at"], rec["notes"]),
        )
        migrated += 1

    log(f"迁移 {migrated} 条价格记录")
    if skipped:
        warn(f"跳过 {skipped} 条")

    # =========================================================
    # 5. 迁移食材层级关系
    # =========================================================
    print("\n=== 5. 迁移食材层级关系 ===")
    bak_hierarchies = bak.execute(
        """SELECT h.*, p.name AS parent_name, c.name AS child_name
           FROM ingredient_hierarchies h
           JOIN ingredients p ON h.parent_id = p.id
           JOIN ingredients c ON h.child_id = c.id
           ORDER BY h.id"""
    ).fetchall()

    hier_migrated = 0
    hier_skipped = 0
    existing_rels = set()
    for r in new.execute(
        "SELECT p.name, c.name, h.relation_type FROM ingredient_hierarchies h "
        "JOIN ingredients p ON h.parent_id = p.id "
        "JOIN ingredients c ON h.child_id = c.id"
    ).fetchall():
        existing_rels.add((r[0], r[1], r[2]))

    for h in bak_hierarchies:
        p_name = h["parent_name"]
        c_name = h["child_name"]
        if (p_name, c_name, h["relation_type"]) in existing_rels:
            continue
        new_parent_id = ing_name_to_new_id.get(p_name)
        new_child_id = ing_name_to_new_id.get(c_name)
        if not new_parent_id:
            warn(f"层级关系: parent「{p_name}」不存在，跳过")
            hier_skipped += 1
            continue
        if not new_child_id:
            warn(f"层级关系: child「{c_name}」不存在，跳过")
            hier_skipped += 1
            continue
        new.execute(
            """INSERT INTO ingredient_hierarchies
               (parent_id, child_id, relation_type, strength,
                created_at, updated_at, created_by, updated_by, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_parent_id, new_child_id, h["relation_type"], h["strength"],
             h["created_at"], h["updated_at"], None, None, 1),
        )
        hier_migrated += 1

    log(f"迁移 {hier_migrated} 条层级关系")
    if hier_skipped:
        warn(f"跳过 {hier_skipped} 条")

    # =========================================================
    # 6. 迁移实体单位覆盖
    # =========================================================
    print("\n=== 6. 迁移实体单位覆盖 ===")
    new_overrides = set()
    for r in new.execute(
        "SELECT entity_type, entity_id, unit_name FROM entity_unit_overrides"
    ).fetchall():
        new_overrides.add((r["entity_type"], r["entity_id"], r["unit_name"]))

    bak_overrides = bak.execute(
        """SELECT e.*, i.name AS ing_name
           FROM entity_unit_overrides e
           LEFT JOIN ingredients i ON e.entity_id = i.id AND e.entity_type = 'ingredient'
           ORDER BY e.id"""
    ).fetchall()

    ov_migrated = 0
    ov_skipped = 0
    for ov in bak_overrides:
        new_entity_id = None
        if ov["entity_type"] == "ingredient":
            new_entity_id = ing_name_to_new_id.get(ov["ing_name"]) if ov["ing_name"] else None
        elif ov["entity_type"] == "product":
            prod_row = bak.execute(
                "SELECT name FROM products WHERE id = ?", (ov["entity_id"],)
            ).fetchone()
            if prod_row:
                new_entity_id = prod_name_to_new_id.get(prod_row["name"])
        if new_entity_id is None:
            warn(f"实体单位覆盖: {ov['entity_type']} id={ov['entity_id']} 映射失败，跳过")
            ov_skipped += 1
            continue
        if (ov["entity_type"], new_entity_id, ov["unit_name"]) in new_overrides:
            continue
        new.execute(
            """INSERT INTO entity_unit_overrides
               (entity_type, entity_id, unit_name, base_unit_id,
                conversion_factor, weight_per_unit, weight_unit_id,
                is_default, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ov["entity_type"], new_entity_id, ov["unit_name"],
             ov["base_unit_id"], ov["conversion_factor"],
             ov["weight_per_unit"], ov["weight_unit_id"],
             ov["is_default"], ov["source"],
             ov["created_at"], ov["updated_at"]),
        )
        ov_migrated += 1

    log(f"迁移 {ov_migrated} 条单位覆盖")
    if ov_skipped:
        warn(f"跳过 {ov_skipped} 条")

    # =========================================================
    # 提交 & 清理
    # =========================================================
    new.commit()
    new.execute("PRAGMA foreign_keys = ON")
    bak.close()
    new.close()

    print("\n" + "=" * 40)
    print("🎉 迁移完成！")
    new_merchants_count = sum(1 for n in merchant_name_to_new_id if n not in new_merchant_names)
    print(f"   商家:      {new_merchants_count} 条新插入 (+{len(merchant_name_to_new_id)} 总映射)")
    print(f"   食材:      {len(missing_ingredients)} 条新插入")
    print(f"   商品:      {len(missing_products)} 条新插入")
    print(f"   价格记录:   {migrated} 条")
    print(f"   层级关系:   {hier_migrated} 条")
    print(f"   单位覆盖:   {ov_migrated} 条")
    print("=" * 40)


if __name__ == "__main__":
    main()
