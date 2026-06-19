"""controlled_db_mcp - 受控的只读数据库 MCP 服务。

架构定位（spike 方案 B，务必遵守）：
- 本 MCP **只暴露只读工具**（``db_read`` / ``describe`` / ``list_tables``）。
- **没有任何 write 工具**——Agent 经 MCP 没有写库路径。
- Agent 要写库时，在 assistant 文本里输出 SQL（```sql``` 围栏块），
  主后端用 sql_extractor 解析 → sql_guard 判危险 → Task 4/5 执行/审批。
- 本模块**不做**写执行/审批逻辑。

工具说明：
- ``db_read(sql)``：用 sql_guard 判定，**非 SELECT 拒绝**（不执行）；SELECT 用
  sqlalchemy 执行，结果转 markdown 表格，截断到 ``max_rows`` 行；异常友好返回。
- ``describe(table_name)``：返回某表的列名/类型（markdown）。
- ``list_tables()``：返回所有表名列表。

运行方式：
- 作为独立 stdio 进程启动（``build_server(db_url).run(transport="stdio")``）。
- ``db_url`` 由调用方（主后端拉起子进程时）注入，本进程自建 engine。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.services.agent.sql_guard import classify_sql, strip_comments

try:  # FastMCP 来自 mcp 包；import 失败时给出清晰报错。
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover - 环境问题，运行时才触发
    raise ImportError(
        "未安装 mcp 包。请在对应虚拟环境中安装：uv pip install mcp "
        "(FastMCP 来自 mcp.server.fastmcp)"
    ) from e


# db_read 读通道的严格只读层：**任何**在深度 0（顶层）出现的写关键字都拒绝。
# 比 sql_guard._TOPLEVEL_WRITE_KEYWORDS 更严：连 INSERT 也拒（db_read 不允许任何写，
# 即使 INSERT 在审批路径是 safe）。顶层 INTO 一律拒（SELECT INTO）。
_READ_GUARD_WRITE_KEYWORDS = (
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
    "INTO",
)


def _strip_literals(sql: str) -> str:
    """抹掉字符串字面量，避免字符串内的写关键字被误判为顶层写。"""
    import re

    sql = re.sub(r"'(?:[^']|'')*'", " ", sql)
    sql = re.sub(r'"(?:[^"]|"")*"', " ", sql)
    return sql


def _has_toplevel_write(stmt: str) -> str | None:
    """db_read 写检测：返回首个「危险」关键字，否则 None。

    策略（db_read 是只读通道，误拒优于误放）：
    - **任意深度**出现写关键字（INSERT/UPDATE/DELETE/REPLACE/CREATE/DROP/
      ALTER/TRUNCATE/ATTACH/DETACH/PRAGMA/GRANT/REVOKE/MERGE/CALL）即拒。
      这同时挡住 CTE 尾语句写（``WITH ... UPDATE``）、data-modifying CTE
      （``WITH d AS (DELETE FROM t RETURNING *) SELECT``，DELETE 在体内深度>=1）。
    - **顶层（深度 0）**出现 INTO 即拒（SELECT INTO 建表 / INTO OUTFILE 写文件）；
      子查询里的 INTO（如 ``SELECT ... IN (SELECT ... INTO ...)``，罕见）也拒——
      保守。
    """
    import re

    cleaned = _strip_literals(stmt)
    depth = 0
    for m in re.finditer(r"\(|\)|[A-Za-z_]+", cleaned):
        tok = m.group(0).upper()
        if tok == "(":
            depth += 1
            continue
        if tok == ")":
            if depth > 0:
                depth -= 1
            continue
        # 任意深度的写关键字都拒（含 CTE 体内的 DELETE/INSERT 等）。
        if tok in _READ_GUARD_WRITE_KEYWORDS and tok != "INTO":
            return tok
        if depth == 0 and tok == "INTO":
            return tok
    return None


def _is_select_with_only(sql: str) -> tuple[bool, str]:
    """纯只读判定（db_read 读通道的严格只读层，C1 修复后）。

    与 ``sql_guard.classify_sql`` 不同：classify_sql 把 INSERT 判 safe、
    带 WHERE 的 UPDATE 判 safe（那是给 sql_extractor 提取的写 SQL 走审批用的）。
    而 ``db_read`` 是 MCP 的**读通道**，方案 B 要求 Agent 经 MCP 没有任何写库
    路径，因此这里更严格——**每一条**子语句都必须是「纯只读」：

    1. 必须以 ``SELECT`` 或 ``WITH`` 开头（CTE）。
    2. **整条语句的顶层（深度 0）**不得出现任何写关键字
       （INSERT/UPDATE/DELETE/REPLACE/CREATE/DROP/ALTER/TRUNCATE/.../INTO）。
       —— 这挡住：``WITH ... UPDATE/DELETE/INSERT``、data-modifying CTE
       （``WITH d AS (DELETE...) SELECT``，因为 DELETE 在 CTE 体内深度>=1 不算，
       但 ``WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d`` 这种
       **data-modifying CTE 本身就是写**——见下方 RETURNING/CTE 体内写检测）、
       以及 ``SELECT ... INTO``。

    C1 历史 bug：原实现只看首词，``WITH`` 开头一律放行，导致
    ``WITH t AS (SELECT 1) UPDATE ...`` 绕过只读层写库。

    Args:
        sql: 原始 SQL 文本，可能含多条语句、注释、前后空白。

    Returns:
        (ok, reason)：ok=True 表示纯只读可执行；ok=False 时 reason 给出中文原因。
    """
    if sql is None:
        return False, "SQL 为 None"
    cleaned = strip_comments(sql).strip()
    if not cleaned:
        return False, "空语句"

    found_any = False
    for part in cleaned.split(";"):
        stmt = part.strip()
        if not stmt:
            continue
        found_any = True
        upper = stmt.upper()
        words = upper.split()
        first_word = words[0] if words else ""

        # 1) 必须以 SELECT / WITH 开头。
        if first_word not in ("SELECT", "WITH"):
            return False, (
                f"非只读语句（首词: {first_word}）——db_read 仅接受 SELECT / WITH"
            )

        # 2) 顶层不得有写关键字（含 INTO）。
        kw = _has_toplevel_write(stmt)
        if kw is not None:
            return False, f"语句含顶层写操作: {kw}（db_read 为只读通道）"

    if not found_any:
        return False, "空语句"
    return True, ""


def _db_read(engine: Engine, sql: str, max_rows: int) -> str:
    """db_read 工具的守卫 + 执行核心逻辑（纯函数，便于单测）。

    流程：
    1. SELECT/WITH-only 严格判定（方案 B 读通道安全层）——每条子语句必须以
       SELECT/WITH 开头，否则拒绝、不执行。
    2. 保留 ``classify_sql`` 作为第二层（DELETE/DROP/ALTER 等仍由它拦）；
       双层冗余更安全。
    3. 通过两层后用 sqlalchemy 执行，结果转 markdown，截断到 ``max_rows``。

    Args:
        engine: SQLAlchemy engine（由 build_server 闭包内创建并注入）。
        sql: 用户/Agent 提交的 SQL 文本。
        max_rows: 返回的最大行数。

    Returns:
        markdown 表格字符串；被拒或出错时返回友好的中文提示。
    """
    reject_hint = (
        "db_read 是只读通道，仅允许 SELECT / WITH ... SELECT 查询。"
        "如需写操作（INSERT/UPDATE/DELETE/DDL），请在回复中以 ```sql 代码块"
        "输出 SQL，由主后端 sql_extractor 解析后走 Task 4/5 审批流程。"
    )

    # 第一层：SELECT/WITH-only（最严格，方案 B 核心原则）。
    ok, reason = _is_select_with_only(sql)
    if not ok:
        return f"拒绝执行：{reason}。{reject_hint}"

    # 第二层：classify_sql（冗余兜底，DELETE/DROP/ALTER 等仍在此拦）。
    verdict = classify_sql(sql)
    if verdict.dangerous:
        return f"拒绝执行：该 SQL 被判定为危险（{verdict.reason}）。{reject_hint}"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
        if not columns:
            return "查询未返回列。"
        return _results_to_markdown(rows, columns, max_rows)
    except Exception as e:  # noqa: BLE001 - MCP 工具需友好兜底
        return f"查询执行失败：{type(e).__name__}: {e}"


def _results_to_markdown(rows: list[Any], columns: list[str], max_rows: int) -> str:
    """把查询结果转为 markdown 表格，截断到 max_rows 行。"""
    truncated = len(rows) > max_rows
    shown = rows[:max_rows]

    def _cell(v: Any) -> str:
        if v is None:
            return "NULL"
        return str(v).replace("|", "\\|").replace("\n", " ")

    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body_lines = []
    for row in shown:
        if hasattr(row, "_mapping"):
            # SQLAlchemy Row 对象：支持 _mapping 访问
            cells = [_cell(row._mapping.get(c)) for c in columns]
        else:
            cells = [_cell(row[i]) for i in range(len(columns))]
        body_lines.append("| " + " | ".join(cells) + " |")

    out = [header, sep] + body_lines
    if truncated:
        out.append(f"\n*(已截断：共 {len(rows)} 行，仅显示前 {max_rows} 行)*")
    return "\n".join(out)


def build_server(db_url: str, *, max_rows: int = 200) -> "FastMCP":
    """构建受控只读数据库 MCP 服务。

    Args:
        db_url: SQLAlchemy 数据库连接字符串（如 ``sqlite:///data/livecalc.db``）。
        max_rows: ``db_read`` 返回的最大行数，默认 200。

    Returns:
        配置好三个只读工具的 ``FastMCP`` 实例（尚未 ``run``）。
    """
    mcp = FastMCP("controlled_db")
    # 引擎在闭包内创建，供所有工具复用。SQLite 需关 check_same_thread（MCP server
    # 可能在不同线程执行查询）。
    connect_args: dict[str, Any] = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine: Engine = create_engine(db_url, connect_args=connect_args)

    @mcp.tool()
    def db_read(sql: str) -> str:
        """执行只读 SELECT 查询，返回 markdown 表格。

        非 SELECT 语句（INSERT/UPDATE/DELETE/DROP/ALTER 等）会被拒绝——
        本工具仅用于读取，写操作请走 assistant 文本 + sql_extractor + 审批流程。

        Args:
            sql: 一条 SELECT 查询（含 WITH ... SELECT 也允许）。

        Returns:
            markdown 表格字符串；出错时返回友好的错误提示。
        """
        # 薄包装：守卫 + 执行逻辑抽到模块级纯函数 _db_read，便于单测。
        return _db_read(engine, sql, max_rows)

    @mcp.tool()
    def describe(table_name: str) -> str:
        """返回指定表的列名与类型（markdown 表格）。

        Args:
            table_name: 表名。

        Returns:
            markdown 表格（列：name / type / nullable / primary_key）；
            出错时返回友好错误。
        """
        try:
            inspector = inspect(engine)
            cols = inspector.get_columns(table_name)
            if not cols:
                return f"未找到表 '{table_name}' 或该表无列。"
            pk = set(inspector.get_pk_constraint(table_name).get("constraint_columns", []) or [])
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

    @mcp.tool()
    def list_tables() -> str:
        """返回数据库中所有表名的 markdown 列表。

        Returns:
            按行列出表名；出错时返回友好错误。
        """
        try:
            inspector = inspect(engine)
            names = inspector.get_table_names()
            if not names:
                return "（数据库中无表）"
            lines = [f"- {n}" for n in names]
            return f"共 {len(names)} 张表：\n" + "\n".join(lines)
        except Exception as e:  # noqa: BLE001
            return f"列出表失败：{type(e).__name__}: {e}"

    return mcp


def _resolve_db_url(argv: "list[str] | None" = None) -> str:
    """解析 db_url：优先 env（``LIVECALC_DB_URL``），其次 argv[1]，兜底默认。

    由 ``runner_factory.make_mcp_config_path`` 生成的 mcp_config 通过 ``env``
    字段注入 ``LIVECALC_DB_URL``，比 argv 更稳（避免路径含空格/转义问题）；
    argv 与默认值作为兼容入口（手动调试用）。
    """
    import os
    import sys

    env_url = os.environ.get("LIVECALC_DB_URL")
    if env_url:
        return env_url
    args = argv if argv is not None else sys.argv[1:]
    if args:
        return args[0]
    return "sqlite:///data/livecalc.db"


if __name__ == "__main__":  # pragma: no cover - 手动启动入口
    url = _resolve_db_url()
    build_server(url).run(transport="stdio")
