"""db_query CLI 回归测试：重构 check_read_only 后行为不变。

验证：
- check_read_only 对 SELECT 放行、对写语句拒绝；
- _reject_non_select 对写语句调 sys.exit(1)（CLI 行为不变）；
- _format_rows 正确输出 markdown。
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from app.services.agent.db_query import (
    _format_rows,
    _reject_non_select,
    check_read_only,
)

# backend 根目录（tests/agent/ 的上两级），用于子进程 cwd，避免依赖 pytest 启动位置
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


# --------------------------------------------------------------------------- #
# check_read_only 纯函数判定
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "  select id from t  ",
        "WITH cte AS (SELECT 1) SELECT * FROM cte",
        "SELECT a FROM t WHERE b = 'INSERT'",  # 字面量内的写关键字不误判
    ],
)
def test_check_read_only_accepts_select(sql):
    ok, reason = check_read_only(sql)
    assert ok, f"应放行: {sql} (原因: {reason})"


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM t WHERE id=1",
        "UPDATE t SET x=1",
        "INSERT INTO t VALUES (1)",
        "DROP TABLE t",
        "ALTER TABLE t ADD COLUMN x INT",
        "CREATE TABLE t2 (id INT)",
        "TRUNCATE t",
        "SELECT * INTO new_t FROM t",  # SELECT INTO
        "WITH d AS (SELECT 1) UPDATE t SET x=2",  # CTE 尾语句写
        "PRAGMA table_info(t)",
    ],
)
def test_check_read_only_rejects_write(sql):
    ok, reason = check_read_only(sql)
    assert not ok, f"应拒绝: {sql}"
    assert reason  # 有拒绝原因


def test_check_read_only_handles_empty_and_none():
    assert check_read_only(None)[0] is False
    assert check_read_only("")[0] is False
    assert check_read_only("   ")[0] is False
    assert check_read_only(";")[0] is False


# --------------------------------------------------------------------------- #
# _reject_non_select CLI 行为：写语句 sys.exit(1)，SELECT 不抛
# --------------------------------------------------------------------------- #
def test_reject_non_select_exits_on_write():
    with pytest.raises(SystemExit) as exc:
        _reject_non_select("DELETE FROM t WHERE id=1")
    assert exc.value.code == 1


def test_reject_non_select_passes_on_select():
    # SELECT 不应抛 SystemExit
    _reject_non_select("SELECT id FROM t")


def test_reject_non_select_exits_on_select_into():
    with pytest.raises(SystemExit):
        _reject_non_select("SELECT * INTO new_t FROM t")


# --------------------------------------------------------------------------- #
# _format_rows markdown
# --------------------------------------------------------------------------- #
def test_format_rows_basic():
    out = _format_rows([(1, "a"), (2, None)], ["id", "name"])
    assert "| id | name |" in out
    assert "| --- | --- |" in out
    assert "| 1 | a |" in out
    assert "| 2 | NULL |" in out


def test_format_rows_empty():
    assert _format_rows([], ["id"]) == "(0 rows)"


# --------------------------------------------------------------------------- #
# CLI 子进程：非 SELECT 退出码 1（端到端回归，覆盖 main 入口）
# --------------------------------------------------------------------------- #
def test_cli_rejects_non_select_exit_code():
    """python -m app.services.agent.db_query 'DELETE FROM t' 应以 exit 1 退出。"""
    proc = subprocess.run(
        [sys.executable, "-m", "app.services.agent.db_query", "DELETE FROM t"],
        capture_output=True,
        text=True,
        cwd=_BACKEND_ROOT,
        env={**os.environ, "PYTHONPATH": _BACKEND_ROOT},
    )
    assert proc.returncode == 1
    assert "SELECT" in proc.stderr or "错误" in proc.stderr
