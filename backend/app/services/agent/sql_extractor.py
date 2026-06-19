"""sql_extractor - 从 assistant 文本中提取 ```sql``` 围栏代码块内容。

用途：Agent 在回复中以 markdown 围栏代码块输出待执行 SQL（写操作无 MCP 工具路径，
见 spike 方案 B）。本模块解析这些代码块，交给 sql_guard 判定、再由 Task 4/5 执行/审批。

设计要点：
- 只认「围栏代码块」：以 ``` 开头、``` 结尾的代码块（三反引号）。
- 语言标记可选：```sql / ```SQL / 无标记 ``` 均视为 SQL 块。
  （注意：为了与 spike 行为一致，无语言标记的围栏块也提取——因为 Agent 写 SQL 时
   通常会带 sql 标记，但稳妥起见两者都支持。）
- 行内反引号 `...`（单个反引号）不视为代码块，不提取。
- 每个块内容仅 strip 首尾空白/换行，内部换行原样保留。
"""
from __future__ import annotations

import re

# 围栏代码块：
#   - 起始：行首（允许前导空白）``` 后跟可选语言标记（sql/SQL 或空），再跟到行尾的杂项
#   - 内容：任意字符（DOTALL）
#   - 结束：行首 ``` 后到行尾
# 用 [^\n]* 容忍 ```sql 之后的尾部空白/标题。
_FENCE_RE = re.compile(
    r"^[ \t]*```[ \t]*(?:sql|SQL)?[^\n]*\n(.*?)^[ \t]*```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)


def extract_sqls(text: str) -> list[str]:
    """从 markdown 文本中提取所有围栏 SQL 代码块的内容。

    Args:
        text: assistant 原始回复文本。

    Returns:
        每个匹配到的代码块内容（已 strip 首尾空白），按出现顺序排列。
        无代码块时返回 ``[]``。
    """
    if not text:
        return []
    return [m.group(1).strip() for m in _FENCE_RE.finditer(text)]
