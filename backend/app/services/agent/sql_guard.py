"""sql_guard - SQL 危险性静态判定。

用途：对从 assistant 文本中提取出的 SQL（或受控 db_read 入参）做白名单/黑名单判定，
决定该 SQL 能否被（在 Task 4/5 中）执行或仅作只读查询。

设计要点（与 spike 结论一致）：
- 纯正则静态分析，不解析 AST，跨引擎兼容（SQLite/MySQL/PostgreSQL）。
- 多语句：以 `;` 切分逐条判定，只要有一条危险则整体危险。
- 判定优先级：DELETE/TRUNCATE/DROP/ALTER 一律危险 → UPDATE 无 WHERE 危险 →
  INSERT/SELECT 安全 → 其它（含未知语句 / 空串）保守判危险。
- 大小写 / 前导空格 / 注释容忍：统一去注释、strip、大写化后匹配。
- WHERE 子句检测：用 `r'\bWHERE\b'` 避免匹配列名中含 "where" 的子串。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "SqlVerdict",
    "classify_sql",
    "strip_comments",
]


@dataclass
class SqlVerdict:
    """SQL 危险性判定结果。

    Attributes:
        dangerous: True 表示该 SQL 不应被自动执行（或被只读工具拒绝）。
        reason: 当 dangerous=True 时给出原因（中文），便于日志/展示。
    """

    dangerous: bool
    reason: str = ""


# 去除行注释 `-- ...` 与块注释 `/* ... */`，避免注释里出现关键字被误判。
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
# 字符串字面量：单引号、双引号（PG 标识符/MySQL 字符串）。用于在扫描写关键字前
# 抹掉字面量，避免字符串里的 INSERT/DELETE 等被误判。
_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")
_DOUBLE_QUOTED_RE = re.compile(r'"(?:[^"]|"")*"')

# 多语句切分：按 `;`（仅在未被引号包裹时切分较复杂；此处保守地直接按 `;` 切，
# 因为我们随后会对每段独立 strip，空段会被忽略，且任何一段命中危险关键字即整体危险）。
_STMT_SPLIT_RE = re.compile(r";")

# 一律危险的关键字（语句开头匹配）。
_DANGEROUS_PREFIXES = ("DELETE", "TRUNCATE", "DROP", "ALTER")
# 安全的前缀（除 UPDATE 需特殊处理 WHERE 外）。
_SAFE_PREFIXES = ("SELECT", "INSERT", "WITH")
# WHERE 子句检测。
_WHERE_RE = re.compile(r"\bWHERE\b")

# 写操作关键字——在「深度 0（顶层，不在任何括号/CTE 内）」出现即判危险。
# 覆盖：CTE 尾语句写（WITH ... UPDATE/DELETE/INSERT/REPLACE）、data-modifying CTE
# （WITH d AS (DELETE...) ...）、SELECT INTO、以及裸 DDL。
# 注意：INSERT 不在此列（INSERT 是 safe 写，由审批路径处理）；UPDATE 在这里单独
# 由无 WHERE 判定兜底。这里主要用于 C1：WITH ... 写 / SELECT INTO。
_TOPLEVEL_WRITE_KEYWORDS = (
    "DELETE",
    "TRUNCATE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
)


def strip_comments(sql: str) -> str:
    """去除 SQL 注释（公开函数，供 controlled_db_mcp 复用）。"""
    sql = _BLOCK_COMMENT_RE.sub(" ", sql)
    sql = _LINE_COMMENT_RE.sub(" ", sql)
    return sql


# 向后兼容别名：历史上 controlled_db_mcp 内联 import 过 _strip_comments。
def _strip_comments(sql: str) -> str:  # pragma: no cover - 薄包装
    return strip_comments(sql)


def _strip_literals(sql: str) -> str:
    """用空格替换字符串字面量，避免字符串内的写关键字被误判为顶层写。"""
    sql = _STRING_LITERAL_RE.sub(" ", sql)
    sql = _DOUBLE_QUOTED_RE.sub(" ", sql)
    return sql


# 这些写关键字出现在 CTE 体内（任意深度）也算危险——data-modifying CTE。
# 注意 INSERT/UPDATE 不在此列：classify_sql 把它们判 safe（审批路径语义）。
_CTE_DANGER_KEYWORDS = (
    "DELETE",
    "TRUNCATE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
)


def _scan_any_write(stmt: str) -> str | None:
    """用于 WITH/SELECT 的写检测：

    - 顶层（深度 0）出现 INTO → 返回 ``INTO``（SELECT INTO 建表/写文件）。
    - 顶层（深度 0）出现 UPDATE / INSERT → 返回该关键字。
      这是 CTE 尾语句写（``WITH ... UPDATE`` / ``WITH ... INSERT``），属写操作，
      必须判 dangerous（与独立的 ``INSERT``/``UPDATE WHERE`` safe 语义不冲突——
      那些以 INSERT/UPDATE 首词走专门分支，不会进入本函数）。
    - 任意深度（含 CTE 体内）出现 data-modifying 写关键字
      （DELETE/TRUNCATE/DROP/ALTER/CREATE/REPLACE/...）→ 返回该关键字。
      这覆盖 PG 的 ``WITH d AS (DELETE ... RETURNING *) SELECT ...``。
    """
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
        if tok in _CTE_DANGER_KEYWORDS:
            return tok
        if depth == 0 and tok in ("UPDATE", "INSERT", "INTO"):
            return tok
    return None


def _has_toplevel_write(stmt: str) -> str | None:
    """扫描去字面量后的语句，返回首个在**深度 0**出现的写关键字，否则 None。

    跟踪括号深度：CTE 的 AS (...) 内部（深度 >= 1）出现的 DELETE/INSERT 等不计；
    只有顶层（WITH ... 后跟的尾语句 / SELECT ... INTO / 裸写语句）才计。

    ``SELECT ... INTO``：INTO 出现在 SELECT 语境（不是 INSERT INTO）即写——
    用 ``\bINTO\b`` 在顶层命中即返回 ``INTO``。
    """
    cleaned = _strip_literals(stmt)
    depth = 0
    # 用单词边界正则在 cleaned 上扫描，逐 token 记录深度。
    # 括号字符单独成 token（更新 depth），其它 token 比对写关键字。
    token_re = re.compile(r"\(|\)|[A-Za-z_]+")
    for m in token_re.finditer(cleaned):
        tok = m.group(0).upper()
        if tok == "(":
            depth += 1
            continue
        if tok == ")":
            if depth > 0:
                depth -= 1
            continue
        if depth == 0:
            if tok in _TOPLEVEL_WRITE_KEYWORDS:
                return tok
            if tok == "INTO":
                # SELECT ... INTO ... / SELECT ... INTO OUTFILE ...：顶层 INTO 即写。
                # （INSERT INTO 由 INSERT 语义；INSERT 未列入写表，但顶层 INTO
                # 只可能来自 SELECT INTO 或 INSERT INTO；二者均不应进 db_read；
                # classify_sql 中 SELECT INTO 判 dangerous。）
                return "INTO"
    return None


def _classify_single(stmt: str) -> SqlVerdict:
    """判定单条 SQL（已 strip、去注释、大写化由调用方保证）。"""
    s = stmt.strip()
    if not s:
        return SqlVerdict(dangerous=True, reason="空语句")

    # 一律危险的前缀。
    for kw in _DANGEROUS_PREFIXES:
        if s == kw or s.startswith(kw + " ") or s.startswith(kw + "\t"):
            return SqlVerdict(dangerous=True, reason=f"包含危险操作: {kw}")

    # UPDATE：无 WHERE 子句即危险（全表更新）。注意：UPDATE 仍在 safe 语义下——
    # 带 WHERE 的 UPDATE 判 safe（这是给审批路径用的）。
    if s == "UPDATE" or s.startswith("UPDATE ") or s.startswith("UPDATE\t"):
        if not _WHERE_RE.search(s):
            return SqlVerdict(
                dangerous=True, reason="UPDATE 缺少 WHERE 子句（将更新全表）"
            )
        return SqlVerdict(dangerous=False)

    # C1 修复：WITH / SELECT 不再一律 safe。
    # - WITH ...：检查是否含写关键字（CTE 尾语句写 / data-modifying CTE）。
    #   INSERT 例外：WITH ... INSERT 仍是 safe 写（与 INSERT safe 语义一致）。
    #   SELECT INTO：顶层 INTO 即 dangerous。
    # - SELECT ...：检查顶层 INTO（PG/MySQL 的 SELECT INTO 建表/写文件）。
    first_word = s.split()[0] if s.split() else ""
    if first_word in ("WITH", "SELECT"):
        write_kw = _scan_any_write(s)
        if write_kw is not None:
            if write_kw == "INTO":
                return SqlVerdict(
                    dangerous=True,
                    reason="SELECT ... INTO 会建表/写文件，判为危险",
                )
            return SqlVerdict(
                dangerous=True,
                reason=f"CTE 语句含写操作: {write_kw}",
            )
        return SqlVerdict(dangerous=False)

    # INSERT：安全（审批路径处理）。
    if first_word == "INSERT":
        return SqlVerdict(dangerous=False)

    # 未知语句：保守判危险（conservative）。
    first_word = s.split()[0] if s.split() else ""
    return SqlVerdict(
        dangerous=True,
        reason=f"未知/未识别的语句类型，保守判为危险 (conservative, 首词: {first_word})",
    )


def classify_sql(sql: str) -> SqlVerdict:
    """判定一条（可能含多条以 `;` 分隔的）SQL 的危险性。

    Args:
        sql: 原始 SQL 文本，可能含多条语句、注释、前后空白。

    Returns:
        SqlVerdict：只要任一子语句危险则整体危险；全部安全才安全。
    """
    if sql is None:
        return SqlVerdict(dangerous=True, reason="SQL 为 None")

    cleaned = _strip_comments(sql).strip()
    if not cleaned:
        return SqlVerdict(dangerous=True, reason="空语句")

    # 切分多语句（保留末尾无分号的最后一段）。
    parts = _STMT_SPLIT_RE.split(cleaned)
    for part in parts:
        stmt = part.strip().upper()
        if not stmt:
            continue
        verdict = _classify_single(stmt)
        if verdict.dangerous:
            return verdict
    return SqlVerdict(dangerous=False)
