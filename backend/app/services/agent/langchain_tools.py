"""langchain Agent 的只读数据库工具。

工具名 ``db_read`` / ``describe`` / ``list_tables`` 与 ``task_templates`` 的
prompt 表述对齐，供后续 LangChainRunner（Task 3）挂载到 Agent。

设计要点：
- **复用而非重造**：只读判定逻辑委托给 ``db_query.check_read_only``（与 db_query
  CLI、controlled_db_mcp 的 ``_is_select_with_only`` 同源，避免三处实现漂移）；
  markdown 表格格式化复用 ``db_query._format_rows``。
- **跨库兼容**：``describe`` / ``list_tables`` 用 SQLAlchemy ``inspect``，不使用
  SQLite 专属的 ``PRAGMA table_info``（生产环境用 MySQL/PostgreSQL 时同样适用）。
- **进程内独立 Session**：每个工具调用时从 ``app.core.database.SessionLocal``
  取一个短生命周期 Session，比 Claude Code 的 MCP 子进程轻量。
- **只读绝不杀进程**：``db_read`` 拒绝非 SELECT 时返回中文错误串，**不调用
  ``sys.exit``**（原 db_query CLI 的 exit 行为保留在 ``_reject_non_select`` 内，
  仅供 CLI 使用）。

线程安全：工具在 SQLite 内存库（``sqlite://``，StaticPool 单连接）反射场景下
非线程安全；生产库（MySQL/PostgreSQL/文件 SQLite）与单 Agent 串行调用无此问题。
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from sqlalchemy import inspect, text
from sqlalchemy.exc import NoSuchTableError

from app.services.agent.db_query import _format_rows, check_read_only


def _run_select(sql: str, max_rows: int = 200) -> str:
    """db_read 的执行核心：守卫 + 执行 + markdown 格式化。

    纯函数（非 @tool），便于直接单测；``db_read`` 是它的 langchain 薄包装。

    Args:
        sql: 用户/Agent 提交的 SQL 文本。
        max_rows: 返回的最大行数（超出截断提示）。

    Returns:
        markdown 表格字符串；被拒或出错时返回友好的中文提示。
    """
    reject_hint = (
        "db_read 是只读通道，仅允许 SELECT / WITH ... SELECT 查询。"
        "如需写操作（INSERT/UPDATE/DELETE/DDL），请在回复中以 ```sql 代码块"
        "输出 SQL，由主后端 sql_extractor 解析后走审批流程。"
    )

    ok, reason = check_read_only(sql)
    if not ok:
        return f"拒绝执行：{reason}。{reject_hint}"

    # 延迟 import 避免模块加载期建立 DB 连接（便于单测 monkeypatch SessionLocal）。
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(text(sql))
        rows = result.fetchall()
        col_names = list(result.keys())
        truncated = len(rows) > max_rows
        shown = rows[:max_rows]
        body = _format_rows(shown, col_names)
        if truncated:
            body += f"\n*(已截断：共 {len(rows)} 行，仅显示前 {max_rows} 行)*"
        return body
    except Exception as e:  # noqa: BLE001 - @tool 需友好兜底
        return f"查询执行失败：{type(e).__name__}: {e}"
    finally:
        # 显式 rollback 吞异常，避免 SQLAlchemy 2.x 异常路径下 Session 状态污染连接池
        try:
            db.rollback()
        except Exception:
            pass
        db.close()


def _current_engine() -> Any:
    """从 SessionLocal 取当前 engine（供 inspect 跨库读表结构）。

    每次调用开一个短 Session 拿其 bind，避免在模块加载期建立全局 engine。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        return db.bind
    finally:
        db.close()


@tool
def db_read(sql: str) -> str:
    """执行只读 SELECT 查询，返回 markdown 表格。严禁非 SELECT 语句。

    仅接受以 ``SELECT`` 或 ``WITH`` 开头的查询；含 ``INSERT`` / ``UPDATE`` /
    ``DELETE`` / ``DROP`` / ``ALTER`` / ``INTO`` 等写关键字将被拒绝（不执行）。
    如需写库，请在回复中以 ```sql 代码块输出 SQL，由主后端审批后执行。

    Args:
        sql: 一条 SELECT 查询（含 ``WITH ... SELECT`` 也允许）。

    Returns:
        markdown 表格字符串；被拒或出错时返回友好的中文提示。
    """
    return _run_select(sql)


@tool
def list_tables() -> str:
    """列出数据库所有表名。

    Returns:
        按行列出所有表名；出错时返回友好的中文错误。
    """
    try:
        engine = _current_engine()
        inspector = inspect(engine)
        names = inspector.get_table_names()
        if not names:
            return "（数据库中无表）"
        lines = [f"- {n}" for n in names]
        return f"共 {len(names)} 张表：\n" + "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return f"列出表失败：{type(e).__name__}: {e}"


@tool
def describe(table_name: str) -> str:
    """查看指定表的列结构（列名、类型、是否可空、是否主键）。

    跨库兼容（SQLite / MySQL / PostgreSQL 均可用，基于 SQLAlchemy inspect）。

    Args:
        table_name: 表名。

    Returns:
        markdown 表格（列：name / type / nullable / primary_key）；出错时返回
        友好错误。
    """
    try:
        engine = _current_engine()
        inspector = inspect(engine)
        try:
            cols = inspector.get_columns(table_name)
        except NoSuchTableError:
            return f"未找到表 '{table_name}'"
        if not cols:
            return f"未找到表 '{table_name}' 或该表无列。"
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk = set(pk_constraint.get("constraint_columns", []) or [])
        header = "| name | type | nullable | primary_key |"
        sep = "| --- | --- | --- | --- |"
        lines = [header, sep]
        for c in cols:
            lines.append(
                f"| {c.get('name')} | {c.get('type')} | "
                f"{c.get('nullable', True)} | {c.get('name') in pk} |"
            )
        return "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return f"获取表结构失败：{type(e).__name__}: {e}"


# 供 LangChainRunner 统一挂载（Task 3）：顺序与 task_templates prompt 描述一致。
READ_ONLY_TOOLS = [db_read, list_tables, describe]
