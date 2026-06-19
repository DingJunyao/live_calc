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


def _reject_non_select(sql: str) -> None:
    """拒绝非 SELECT 语句（只允许纯 SELECT 查询）。"""
    import re

    # 抹掉字符串字面量避免误判
    cleaned = re.sub(r"'(?:[^']|'')*'", " ", sql)
    cleaned = re.sub(r'"(?:[^"]|"")*"', " ", cleaned)

    # 检查顶层写关键字（INSERT/UPDATE/DELETE/REPLACE/CREATE/DROP/ALTER/...）
    # 使用 sql_guard 的 classify_sql 作为第一道防线
    verdict = classify_sql(cleaned)
    if verdict.dangerous:
        print(f"错误：只允许 SELECT 查询（{verdict.reason}）", file=sys.stderr)
        sys.exit(1)

    # 即使 classify_sql 未判危险，额外检查顶层写关键字
    _TOPLEVEL_WRITE_KEYWORDS = (
        "INSERT", "UPDATE", "DELETE", "REPLACE",
        "CREATE", "DROP", "ALTER", "TRUNCATE",
        "ATTACH", "DETACH", "PRAGMA",
        "GRANT", "REVOKE", "MERGE", "CALL",
    )
    # 取第一个非空白 token
    first_token = cleaned.lstrip().split(None, 1)[0] if cleaned.strip() else ""
    if first_token.upper() in _TOPLEVEL_WRITE_KEYWORDS:
        print(f"错误：只允许 SELECT 查询（检测到 {first_token}）", file=sys.stderr)
        sys.exit(1)
    # SELECT INTO 也拒
    if re.search(r"\bINTO\b", cleaned, re.IGNORECASE):
        print("错误：检测到 INTO 关键字（SELECT INTO 不允许）", file=sys.stderr)
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
        print("用法: python -m app.services.agent.db_query <SQL 查询>", file=sys.stderr)
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
