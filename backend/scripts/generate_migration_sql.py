# -*- coding: utf-8 -*-
"""生成兼容多数据库引擎的 SQL 迁移脚本"""
import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path("d:/code/live_calc")
NEW_DB = PROJECT_ROOT / "backend" / "data" / "livecalc.db"
MAPPING_FILE = PROJECT_ROOT / "backend" / "scripts" / "migration_mapping.json"
SQL_OUTPUT = PROJECT_ROOT / "backend" / "scripts" / "migration_data.sql"

conn = sqlite3.connect(str(NEW_DB))
conn.row_factory = sqlite3.Row

with open(MAPPING_FILE, "r", encoding="utf-8") as f:
    mapping = json.load(f)

lines = []


def emit(s=""):
    lines.append(s)


def sql_val(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"


def emit_insert(table, data_dict):
    cols = [k for k, v in data_dict.items() if v is not None]
    vals = [sql_val(data_dict[c]) for c in cols]
    emit(f"INSERT INTO {table} ({', '.join(cols)})")
    emit(f"VALUES ({', '.join(vals)});")
    emit()


emit("-- ============================================================")
emit("-- 数据迁移 SQL 脚本")
emit("-- 生成时间: 2026-06-05")
emit("-- 源数据库: livecalc_bak.db (旧版本)")
emit("-- 目标数据库: livecalc.db (新版本)")
emit("-- ============================================================")
emit("-- 兼容: SQLite / MySQL / PostgreSQL")
emit("-- 注意事项:")
emit("--   1. MySQL 需要 LAST_INSERT_ID() 获取自增ID")
emit("--   2. PostgreSQL 需要 RETURNING id 或使用 SEQUENCE")
emit("--   3. 字段名使用下划线命名法（snake_case），需确认目标表结构一致")
emit("--   4. 日期格式为 ISO 8601 字符串")
emit("-- ============================================================")
emit()

# 1. 用户
emit("-- ============================================================")
emit("-- 1. 用户")
emit("-- ============================================================")
user = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
user_cols = [desc[0] for desc in conn.execute("SELECT * FROM users LIMIT 0").description]
user_data = {}
for c in user_cols:
    if c == "id":
        continue
    user_data[c] = dict(user).get(c)
emit_insert("users", user_data)
emit(f"-- 新用户 ID = {mapping['new_user_id']}")
emit()

# 2. 商家
emit("-- ============================================================")
emit("-- 2. 商家")
emit("-- ============================================================")
merchants = conn.execute("SELECT * FROM merchants ORDER BY id").fetchall()
merchant_cols = [desc[0] for desc in conn.execute("SELECT * FROM merchants LIMIT 0").description]
for m in merchants:
    m_dict = {c: m[c] for c in merchant_cols if c != "id"}
    old_ids = [k for k, v in mapping["merchant_id_mapping"].items() if str(v) == str(m["id"])]
    old_id_str = old_ids[0] if old_ids else "?"
    emit(f"-- 旧ID={old_id_str}, 新ID={m['id']}")
    emit_insert("merchants", m_dict)

# 3. 新建原料
emit("-- ============================================================")
emit("-- 3. 新建原料（旧库商品无法匹配新库原料时创建）")
emit("-- ============================================================")
new_ingredients = conn.execute(
    "SELECT * FROM ingredients WHERE id > 640 ORDER BY id"
).fetchall()
ing_cols = [desc[0] for desc in conn.execute("SELECT * FROM ingredients LIMIT 0").description]
for ing in new_ingredients:
    i_dict = {c: ing[c] for c in ing_cols if c != "id"}
    emit(f"-- 新建原料 ID={ing['id']}")
    emit_insert("ingredients", i_dict)

# 4. 新建商品
emit("-- ============================================================")
emit("-- 4. 新建商品（旧库商品无法匹配新库商品时创建）")
emit("-- ============================================================")
new_products = conn.execute(
    "SELECT * FROM products WHERE id > 618 ORDER BY id"
).fetchall()
prod_cols = [desc[0] for desc in conn.execute("SELECT * FROM products LIMIT 0").description]
for p in new_products:
    p_dict = {c: p[c] for c in prod_cols if c != "id"}
    emit(f"-- 新建商品 ID={p['id']}: {p['name']}")
    emit_insert("products", p_dict)

# 5. 价格记录
emit("-- ============================================================")
emit("-- 5. 价格记录")
emit("-- ============================================================")
emit(f"-- 共 {mapping['records_migrated']} 条")
emit()

records = conn.execute(
    "SELECT * FROM product_records ORDER BY id"
).fetchall()
record_cols = [desc[0] for desc in conn.execute("SELECT * FROM product_records LIMIT 0").description]

# 分批输出，每100条一个注释
batch_size = 100
for i, r in enumerate(records):
    if i % batch_size == 0:
        emit(f"-- --- 批次 {i // batch_size + 1} (记录 {i + 1}-{min(i + batch_size, len(records))}) ---")
    r_dict = {c: r[c] for c in record_cols if c != "id"}
    emit_insert("product_records", r_dict)

# 统计
emit("-- ============================================================")
emit("-- 迁移统计")
emit("-- ============================================================")
emit(f"-- 用户: 1 条")
emit(f"-- 商家: {len(merchants)} 条")
emit(f"-- 新建原料: {len(new_ingredients)} 个")
emit(f"-- 新建商品: {len(new_products)} 个")
emit(f"-- 价格记录: {len(records)} 条")
emit(f"-- 总计 INSERT 语句: {len([l for l in lines if l.startswith('INSERT')])} 条")

conn.close()

# 写入文件
with open(SQL_OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"SQL script generated: {SQL_OUTPUT}")
print(f"Total lines: {len(lines)}")
