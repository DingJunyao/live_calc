"""db_query - Agent 通过 bash 调用的数据库查询帮助脚本。

当 ``mcp`` 包不可用时，Agent 没有受控 MCP 的只读工具可用。
此脚本作为替代：Agent 在 bash 中调用 ``python -m app.services.agent.db_query "SELECT ..."``
来执行只读查询，结果以 markdown 表格形式输出到 stdout。

Usage:
    python -m app.services.agent.db_query "SELECT * FROM ingredients LIMIT 5"

安全性：
- 脚本内部通过 sql_guard 判定，**非 SELECT 直接拒绝**，与受控 MCP 的 db_read 一致。
- 仅在非 MCP 模式下使用；MCP 可用时仍然走受控 MCP 的 db_read 工具。
"""

from __future__ import annotations

import json
import sys

from sqlalchemy import text

from app.services.agent.sql_guard import classify_sql, strip_comments


def check_read_only(sql: str) -> "tuple[bool, str]":
    """判定 SQL 是否为纯只读 SELECT（db_query CLI 与 langchain_tools 共用）。

    与 ``controlled_db_mcp._is_select_with_only`` 策略一致：仅允许 SELECT / WITH
    开头、不得出现顶层写关键字、不得出现 INTO。判定逻辑以纯函数形式提供，供：

    - ``db_query._reject_non_select``（CLI 入口，非只读时 ``sys.exit(1)``，保持
      既有行为不变）；
    - ``langchain_tools.db_read``（@tool 进程内调用，非只读时返回中文错误串而非
      杀进程）。

    复用同一逻辑避免两处实现漂移。

    Args:
        sql: 原始 SQL 文本，可能含多条语句、注释、字面量。

    Returns:
        ``(ok, reason)``：``ok=True`` 表示纯只读可执行；``ok=False`` 时 ``reason``
        为中文拒绝原因。
    """
    import re

    if sql is None:
        return False, "SQL 为 None"
    # 抹掉字符串字面量避免误判
    cleaned = re.sub(r"'(?:[^']|'')*'", " ", sql)
    cleaned = re.sub(r'"(?:[^"]|"")*"', " ", cleaned)
    cleaned = strip_comments(cleaned).strip()

    if not cleaned:
        return False, "空语句"

    # 即使 classify_sql 未判危险，额外检查顶层写关键字
    # 注意：与 controlled_db_mcp._READ_GUARD_WRITE_KEYWORDS 故意不同——
    # 此处额外含 MERGE/CALL/GRANT/REVOKE；INTO 由下方 regex 单独处理
    # （controlled_db_mcp 把 INSERT 也列进来是因为它走更严的读通道）。
    _TOPLEVEL_WRITE_KEYWORDS = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "REPLACE",
        "CREATE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "GRANT",
        "REVOKE",
        "MERGE",
        "CALL",
    )
    found_any = False
    for part in cleaned.split(";"):
        stmt = part.strip()
        if not stmt:
            continue
        found_any = True
        upper = stmt.upper()
        words = upper.split()
        first_word = words[0] if words else ""

        # 必须以 SELECT / WITH 开头
        if first_word not in ("SELECT", "WITH"):
            return False, f"非只读语句（首词: {first_word}）——仅接受 SELECT / WITH"

        # 语句不完整（裸 SELECT / WITH，无后续 body）
        if len(words) < 2:
            return False, "语句不完整"

        # classify_sql 作为冗余兜底（DELETE/DROP/ALTER 等仍在此拦）
        verdict = classify_sql(stmt)
        if verdict.dangerous:
            return False, verdict.reason

        # 首词为写关键字（多语句里第二条可能是 UPDATE 等）
        if first_word in _TOPLEVEL_WRITE_KEYWORDS:
            return False, f"检测到 {first_word}"

        # SELECT INTO 也拒
        if re.search(r"\bINTO\b", stmt, re.IGNORECASE):
            return False, "检测到 INTO 关键字（SELECT INTO 不允许）"

    if not found_any:
        return False, "空语句"
    return True, ""


def _reject_non_select(sql: str) -> None:
    """拒绝非 SELECT 语句（CLI 入口专用，保持原 sys.exit 行为不变）。

    判定逻辑委托给模块级 ``check_read_only``；此处仅负责把拒绝原因打到 stderr
    并以非零状态退出。
    """
    ok, reason = check_read_only(sql)
    if not ok:
        print(f"错误：只允许 SELECT 查询（{reason}）", file=sys.stderr)
        sys.exit(1)


def _format_rows(rows: list, col_names: list[str]) -> str:
    """把查询结果格式化成 markdown 表格。"""
    if not rows:
        return "(0 rows)"

    lines: list[str] = []
    # 表头
    lines.append("| " + " | ".join(col_names) + " |")
    lines.append("| " + " | ".join("---" for _ in col_names) + " |")

    for row in rows:
        vals: list[str] = []
        for v in row:
            if v is None:
                vals.append("NULL")
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            elif isinstance(v, dict):
                vals.append(json.dumps(v, ensure_ascii=False))
            else:
                s = str(v)
                # 过长的文本截断
                if len(s) > 200:
                    s = s[:197] + "..."
                vals.append(s)
        lines.append("| " + " | ".join(vals) + " |")

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "用法: python -m app.services.agent.db_query <SQL 查询>",
            file=sys.stderr,
        )
        sys.exit(1)

    sql = sys.argv[1]

    # 拒绝非 SELECT
    _reject_non_select(sql)

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(text(sql))
        rows = result.fetchall()
        col_names = list(result.keys())

        output = _format_rows(rows, col_names)
        print(output)
    except Exception as exc:
        print(f"查询失败: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
