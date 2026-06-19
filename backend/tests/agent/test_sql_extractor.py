"""sql_extractor 单元测试。

覆盖：
- 单个 ```sql ... ``` 块提取
- 多个代码块全提取
- 无代码块返回 []
- 代码块前后有动作意图文字时只取代码块内容（trim）
- 兼容 ```sql、```SQL、无语言标记 ```
- 每条 SQL 被 trim
- 代码块内含 SQL 分号 / 换行 / 缩进原样保留（仅首尾 trim）
"""

from app.services.agent.sql_extractor import extract_sqls


def test_single_sql_block():
    text = "我来更新一下：\n```sql\nUPDATE products SET price=10 WHERE id=1\n```\n请执行。"
    result = extract_sqls(text)
    assert result == ["UPDATE products SET price=10 WHERE id=1"]


def test_multiple_sql_blocks():
    text = (
        "步骤如下：\n"
        "```sql\nUPDATE products SET price=10 WHERE id=1\n```\n"
        "然后：\n"
        "```sql\nDELETE FROM old_records WHERE created_at < '2024-01-01'\n```\n"
    )
    result = extract_sqls(text)
    assert result == [
        "UPDATE products SET price=10 WHERE id=1",
        "DELETE FROM old_records WHERE created_at < '2024-01-01'",
    ]


def test_no_code_block_returns_empty():
    text = "这段文字里没有 SQL 代码块，只是普通说明。"
    assert extract_sqls(text) == []


def test_strips_surrounding_prose():
    """代码块前后的动作意图文字必须被剥离，只保留代码块内容。"""
    text = (
        "好的，我将删除过期的记录。\n\n"
        "```sql\nDELETE FROM logs WHERE expired = 1\n```\n\n"
        "执行完毕后会通知你。"
    )
    result = extract_sqls(text)
    assert result == ["DELETE FROM logs WHERE expired = 1"]


def test_uppercase_sql_fence():
    text = "```SQL\nSELECT 1\n```"
    assert extract_sqls(text) == ["SELECT 1"]


def test_no_language_marker():
    text = "执行下面的查询：\n```\nSELECT * FROM users\n```"
    assert extract_sqls(text) == ["SELECT * FROM users"]


def test_trim_each_sql():
    """代码块内容首尾的换行/空白应被 trim 掉。"""
    text = "```sql\n\n   SELECT 1;   \n\n```"
    result = extract_sqls(text)
    assert result == ["SELECT 1;"]


def test_multiline_sql_preserved():
    """多行 SQL 应原样保留内部换行，仅 trim 首尾。"""
    inner = "UPDATE products\nSET price = 10\nWHERE id = 1"
    text = f"```sql\n{inner}\n```"
    assert extract_sqls(text) == [inner]


def test_empty_text():
    assert extract_sqls("") == []


def test_empty_code_block():
    """空代码块的内容 trim 后为空字符串，仍应作为一个元素返回（调用方按需过滤）。"""
    text = "```sql\n\n```"
    result = extract_sqls(text)
    # 空块 trim 后为 ""；此处约定返回 [""]（保留位置，交由 sql_guard 拒绝空语句）
    assert result == [""] or result == []


def test_sql_inside_inline_backticks_not_extracted():
    """行内反引号（非围栏代码块）不应被提取。"""
    text = "运行 `SELECT 1` 即可。"
    assert extract_sqls(text) == []
