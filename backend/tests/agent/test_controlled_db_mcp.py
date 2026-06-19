"""controlled_db_mcp._db_read 守卫单测（方案 B 安全层）。

核心断言：``_db_read`` 作为 MCP 的**读通道**必须严格只读，
**每一条**子语句都必须以 SELECT 或 WITH 开头，否则拒绝（不执行）。

覆盖：
- INSERT → 拒绝、不写入
- UPDATE ... WHERE → 拒绝（即便 classify_sql 判 safe）
- DELETE → 拒绝
- SELECT → 正常返回 markdown
- WITH ... SELECT → 正常返回
- 多语句含非 SELECT（SELECT 1; INSERT ...）→ 拒绝、不写入
- 拒绝信息为友好中文（含 ```sql 提示）
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.services.agent.controlled_db_mcp import _db_read


@pytest.fixture()
def engine_with_table():
    """内存 SQLite + 一张 products(id, name) 表（含 1 行）。

    M3：用 yield + dispose() 确保测试结束释放 engine（避免连接泄漏）。
    """
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    with eng.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(50))"
            )
        )
        conn.execute(text("INSERT INTO products (id, name) VALUES (1, '鸡蛋')"))
        conn.commit()
    yield eng
    eng.dispose()


def _is_rejection(msg: str) -> bool:
    return msg.startswith("拒绝执行") or "只读" in msg or "```sql" in msg


# ---------- INSERT：拒绝且不写入 ----------
def test_insert_rejected_and_not_written(engine_with_table: Engine):
    sql = "INSERT INTO products (id, name) VALUES (2, '鸭蛋')"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"应拒绝 INSERT，实际返回：{msg!r}"
    # 验证确实没写入
    with engine_with_table.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
    assert rows == 1, "INSERT 不应被执行"


# ---------- UPDATE ... WHERE：拒绝 ----------
def test_update_with_where_rejected(engine_with_table: Engine):
    sql = "UPDATE products SET name='鹅蛋' WHERE id=1"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"应拒绝 UPDATE，实际返回：{msg!r}"
    # 验证没改
    with engine_with_table.connect() as conn:
        name = conn.execute(
            text("SELECT name FROM products WHERE id=1")
        ).scalar()
    assert name == "鸡蛋", "UPDATE 不应被执行"


# ---------- DELETE：拒绝 ----------
def test_delete_rejected(engine_with_table: Engine):
    sql = "DELETE FROM products WHERE id=1"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"应拒绝 DELETE，实际返回：{msg!r}"
    with engine_with_table.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
    assert rows == 1, "DELETE 不应被执行"


# ---------- SELECT：正常返回 markdown ----------
def test_select_returns_markdown(engine_with_table: Engine):
    msg = _db_read(engine_with_table, "SELECT id, name FROM products", max_rows=200)
    assert not _is_rejection(msg), f"SELECT 不应被拒，实际返回：{msg!r}"
    assert "|" in msg, "应返回 markdown 表格"
    assert "id" in msg and "name" in msg
    assert "鸡蛋" in msg


# ---------- WITH ... SELECT：正常返回 ----------
def test_with_cte_returns_markdown(engine_with_table: Engine):
    sql = "WITH t AS (SELECT id, name FROM products) SELECT * FROM t"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert not _is_rejection(msg), f"WITH ... SELECT 不应被拒，实际返回：{msg!r}"
    assert "鸡蛋" in msg


# ---------- 多语句含非 SELECT：拒绝且不写入 ----------
def test_multi_statement_with_insert_rejected(engine_with_table: Engine):
    sql = "SELECT 1; INSERT INTO products (id, name) VALUES (5, '鹌鹑蛋')"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"多语句含 INSERT 应被拒，实际返回：{msg!r}"
    with engine_with_table.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
    assert rows == 1, "多语句中的 INSERT 不应被执行"


# ============================================================
# C1 回归：CTE 驱动写语句绕过 db_read 只读通道
# （SQLite/PG/MySQL 都支持 WITH 开头的写语句；原实现只看首词放行）
# ============================================================

def _count_products(eng: Engine) -> int:
    with eng.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM products")).scalar())


def _get_name(eng: Engine, pid: int) -> str:
    with eng.connect() as conn:
        return conn.execute(
            text("SELECT name FROM products WHERE id=:i"), {"i": pid}
        ).scalar()


# --- 攻击 1：WITH ... UPDATE ---
def test_cte_update_rejected_and_not_written(engine_with_table: Engine):
    assert _count_products(engine_with_table) == 1
    sql = "WITH t AS (SELECT 1) UPDATE products SET name='x' WHERE id=1"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"CTE+UPDATE 应被拒，实际返回：{msg!r}"
    assert _count_products(engine_with_table) == 1, "未写入新行"
    assert _get_name(engine_with_table, 1) == "鸡蛋", "原行未被改写"


# --- 攻击 2：WITH ... DELETE ---
def test_cte_delete_rejected_and_not_written(engine_with_table: Engine):
    assert _count_products(engine_with_table) == 1
    sql = "WITH t AS (SELECT 1) DELETE FROM products WHERE id=1"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"CTE+DELETE 应被拒，实际返回：{msg!r}"
    assert _count_products(engine_with_table) == 1, "DELETE 不应执行"


# --- 攻击 3：WITH ... INSERT ---
def test_cte_insert_rejected_and_not_written(engine_with_table: Engine):
    assert _count_products(engine_with_table) == 1
    sql = "WITH t AS (SELECT 1) INSERT INTO products(id,name) VALUES (2,'x')"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"CTE+INSERT 应被拒，实际返回：{msg!r}"
    assert _count_products(engine_with_table) == 1, "INSERT 不应执行"


# --- 攻击 5：SELECT ... INTO（SQLite 不支持，但应返回拒绝而非尝试执行）---
def test_select_into_rejected(engine_with_table: Engine):
    sql = "SELECT * INTO new_table FROM products"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert _is_rejection(msg), f"SELECT ... INTO 应被拒，实际返回：{msg!r}"


# --- 合法只读 CTE：仍正常放行 ---
def test_pure_readonly_cte_returns_markdown(engine_with_table: Engine):
    sql = "WITH t AS (SELECT id FROM products) SELECT * FROM t WHERE id>0"
    msg = _db_read(engine_with_table, sql, max_rows=200)
    assert not _is_rejection(msg), f"纯只读 CTE 不应被拒，实际返回：{msg!r}"
    assert "鸡蛋" in msg or "1" in msg
