"""sql_guard 单元测试。

覆盖：
- SELECT 安全
- DELETE / TRUNCATE / DROP / ALTER 各判危险
- UPDATE 无 WHERE 危险；UPDATE 带 WHERE（含守卫 AND weight_per_unit=100）安全
- INSERT 安全
- 未知语句保守判危险
- 大小写 / 前导空格 / 分号 / 多语句
"""

import pytest

from app.services.agent.sql_guard import SqlVerdict, classify_sql


# ---------- SELECT ----------
def test_select_safe():
    v = classify_sql("SELECT * FROM products")
    assert v.dangerous is False
    assert v.reason == ""


def test_select_with_where_safe():
    v = classify_sql("select id, name from products where id = 1")
    assert v.dangerous is False


def test_select_leading_whitespace_and_case_safe():
    v = classify_sql("   sElEcT 1")
    assert v.dangerous is False


# ---------- DELETE ----------
def test_delete_dangerous():
    v = classify_sql("DELETE FROM products WHERE id = 1")
    assert v.dangerous is True
    assert "DELETE" in v.reason or "delete" in v.reason.lower()


def test_delete_no_where_dangerous():
    v = classify_sql("delete from products")
    assert v.dangerous is True


# ---------- TRUNCATE ----------
def test_truncate_dangerous():
    v = classify_sql("TRUNCATE TABLE products")
    assert v.dangerous is True
    assert "TRUNCATE" in v.reason or "truncate" in v.reason.lower()


# ---------- DROP ----------
def test_drop_dangerous():
    v = classify_sql("DROP TABLE products")
    assert v.dangerous is True
    assert "DROP" in v.reason or "drop" in v.reason.lower()


def test_drop_database_dangerous():
    v = classify_sql("drop database livecalc")
    assert v.dangerous is True


# ---------- ALTER ----------
def test_alter_dangerous():
    v = classify_sql("ALTER TABLE products ADD COLUMN x INTEGER")
    assert v.dangerous is True
    assert "ALTER" in v.reason or "alter" in v.reason.lower()


# ---------- UPDATE ----------
def test_update_no_where_dangerous():
    v = classify_sql("UPDATE products SET price = 10")
    assert v.dangerous is True
    assert "WHERE" in v.reason or "where" in v.reason.lower()


def test_update_with_where_safe():
    v = classify_sql("UPDATE products SET price = 10 WHERE id = 1")
    assert v.dangerous is False


def test_update_with_where_and_guard_safe():
    """守卫型 UPDATE：带额外的 AND 条件（例如 AND weight_per_unit=100）也应安全。"""
    v = classify_sql(
        "UPDATE ingredients SET name='鸡蛋' WHERE id=5 AND weight_per_unit=100"
    )
    assert v.dangerous is False


def test_update_lowercase_with_where_safe():
    v = classify_sql("update products set price=1 where id=2")
    assert v.dangerous is False


# ---------- INSERT ----------
def test_insert_safe():
    v = classify_sql("INSERT INTO products (name) VALUES ('鸡蛋')")
    assert v.dangerous is False


# ---------- 未知语句：保守判危险 ----------
def test_unknown_statement_dangerous():
    """M5：去掉对 reason 文案的脆弱依赖，只验 dangerous。"""
    v = classify_sql("VACUUM")
    assert v.dangerous is True


# ============================================================
# C1 回归：WITH 不再一律判 safe
# ============================================================

# --- 攻击 1：CTE+UPDATE → dangerous ---
def test_cte_update_dangerous():
    v = classify_sql("WITH t AS (SELECT 1) UPDATE products SET name='x' WHERE id=1")
    assert v.dangerous is True


# --- 攻击 2：CTE+DELETE → dangerous ---
def test_cte_delete_dangerous():
    v = classify_sql("WITH t AS (SELECT 1) DELETE FROM products WHERE id=1")
    assert v.dangerous is True


# --- 攻击 3：CTE+INSERT → dangerous ---
def test_cte_insert_dangerous():
    v = classify_sql("WITH t AS (SELECT 1) INSERT INTO products(id,name) VALUES(2,'x')")
    assert v.dangerous is True


# --- 攻击 4：PG data-modifying CTE（DELETE 在 CTE 内，首词 WITH）→ dangerous ---
def test_cte_data_modifying_dangerous():
    v = classify_sql("WITH d AS (DELETE FROM products RETURNING *) SELECT * FROM d")
    assert v.dangerous is True


# --- 攻击 5/6：SELECT INTO → dangerous ---
def test_select_into_dangerous():
    v = classify_sql("SELECT * INTO new_table FROM products")
    assert v.dangerous is True


def test_select_into_outfile_dangerous():
    v = classify_sql("SELECT * FROM products INTO OUTFILE '/tmp/x'")
    assert v.dangerous is True


# --- 合法只读 CTE → safe ---
def test_pure_readonly_cte_safe():
    v = classify_sql("WITH t AS (SELECT id FROM products) SELECT * FROM t WHERE id>0")
    assert v.dangerous is False


def test_empty_string_dangerous():
    v = classify_sql("")
    assert v.dangerous is True


# ---------- 多语句 / 分号 ----------
def test_multiple_statements_first_select_dangerous_if_second_is_delete():
    """多语句：只要有一条危险语句就判危险。"""
    v = classify_sql("SELECT 1; DELETE FROM products;")
    assert v.dangerous is True


def test_multiple_safe_statements_safe():
    v = classify_sql("SELECT 1; SELECT 2;")
    assert v.dangerous is False


def test_statement_with_trailing_semicolon_safe():
    v = classify_sql("SELECT * FROM products;")
    assert v.dangerous is False


# ---------- SqlVerdict 结构 ----------
def test_verdict_dataclass_defaults():
    v = SqlVerdict(dangerous=False)
    assert v.dangerous is False
    assert v.reason == ""
