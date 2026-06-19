"""预设任务模板：title + prompt + allowed_tools（Task 6）。

每个模板对应一类 Agent 维护任务，由 ``agent_api.create_session`` 在建会话时
根据 ``task_type`` 查询并注入为 initial_prompt。

模板字段：
- ``title``：人类可读任务名（前端按钮列表显示）。
- ``prompt``：发给 Agent 的完整指令（含角色/工具/工作流/输出格式约束）。
- ``allowed_tools``：该任务允许 Agent 调用的工具白名单（对齐 runner_factory
  的 controlled_db MCP 暴露面；未来可按任务粒度收紧）。

阶段 1 只实现 ``fill_piece_weight``；``fill_density`` / ``usda_translate``
留阶段 2 占位（不实现 prompt）。
"""
from __future__ import annotations

__all__ = ["TASK_TEMPLATES", "get_template", "list_task_types"]


# controlled_db MCP 暴露的只读工具白名单（与 runner_factory.allowed_tools_for_db
# 对齐）。
_READ_ONLY_TOOLS = [
    "mcp__controlled_db__db_read",
    "mcp__controlled_db__describe",
    "mcp__controlled_db__list_tables",
]


_FILL_PIECE_WEIGHT_PROMPT = """你是「生计」应用的食材数据维护助手，专门负责校准食材自定义单位对应的质量（克）。

# 任务目标
维护 ``entity_unit_overrides`` 表的 ``weight_per_unit`` 字段——记录某种食材的某个
自定义单位（如「干辣椒 1 个」「花椒 1 颗」「鸡蛋 1 个」）对应的克数。当前该字段
存在两类问题：
1. 缺失（NULL）
2. 占位脏数据——历史导入时把未知值统一写成 100，明显不合理（如花椒 1 颗 = 100g
   实际 ~0.02g、干辣椒 1 个 = 100g 实际 ~2-3g）。

# 工具说明（重要）
你只有以下三个**只读**工具可用：
- ``mcp__controlled_db__db_read``：执行 SELECT 查询。
- ``mcp__controlled_db__describe``：查看表结构。
- ``mcp__controlled_db__list_tables``：列出所有表。

**你没有任何写工具**（没有 db_write / db_update / db_delete 等）。需要写库时，
**在你的回复正文里用 ```sql``` 代码块输出 SQL**——系统的 sql_extractor 会自动
提取，sql_guard 判定：
- 安全 SQL（INSERT / 带 WHERE 的 UPDATE）自动执行；
- 危险 SQL（DELETE / 无 WHERE 的 UPDATE / DROP 等）会生成审批记录交给管理员审批。

不要试图调用不存在的写工具，也不要把 SQL 写在普通段落里（必须用 ```sql``` 围栏）。

# 工作流程
按以下步骤推进，每一步先观察再决策：

1. **摸底统计**：用 db_read 对 ``entity_unit_overrides`` 做 GROUP BY 聚类，看清
   ``weight_per_unit`` 字段的分布——重点找 NULL 和 =100 的占位行。建议查询：
   ```sql
   SELECT unit_name, COUNT(*) AS cnt,
          SUM(CASE WHEN weight_per_unit IS NULL THEN 1 ELSE 0 END) AS null_cnt,
          SUM(CASE WHEN weight_per_unit = 100 THEN 1 ELSE 0 END) AS placeholder_cnt,
          MIN(weight_per_unit) AS min_w, MAX(weight_per_unit) AS max_w
   FROM entity_unit_overrides
   GROUP BY unit_name
   ORDER BY placeholder_cnt DESC, null_cnt DESC;
   ```
   再针对高优先级 unit_name 拉 detail（带 entity_type/entity_id 关联
   ingredients 或 products 看具体食材名）。

2. **诊断异常值**：对每条可疑行结合食材常识判断是否合理。参考：
   - 花椒 1 颗 ≈ 0.02g（100g 显然错）
   - 干辣椒 1 个 ≈ 2-3g（100g 显然错）
   - 鸡蛋 1 个 ≈ 50-60g（带壳）
   - 大蒜 1 瓣 ≈ 5g
   - 八角 1 颗 ≈ 1-2g
   - 生姜 1 片 ≈ 3-5g
   对 =100 的占位行，几乎都需要修正。

3. **估算合理克数**：按食材常识给出修正方案，分类整理成清单（食材 / 单位 /
   原值 / 新值 / 依据）。能查到 USDA 或常识值的优先用常识值。

4. **输出修正 SQL**（**关键守卫**）：每条 UPDATE 必须带
   ``WHERE id IN (...) AND weight_per_unit = <原占位值>`` 双重守卫——
   ``id IN`` 限定目标行，``AND weight_per_unit=<原值>`` 防止误改已被其它流程
   修正过的值；``SET source = 'agent'`` 标记本次维护来源。模板：
   ```sql
   UPDATE entity_unit_overrides
   SET weight_per_unit = <新值>, source = 'agent'
   WHERE id IN (<id1>, <id2>, ...) AND weight_per_unit = <原占位值>;
   ```
   每条 UPDATE 独立一个 ```sql``` 围栏块，便于系统逐条提取判级。

5. **复核改动**：执行后用 db_read 再查一次，确认目标行 ``weight_per_unit`` 已
   更新为合理值、``source = 'agent'``，且改动行数与预期一致。

6. **全部自己决策，不问用户**：即使是不常见的食材（地方性香料、进口食材、包装
   规格不清的），也要基于常识/典型包装/经验给出**合理的估计值**直接修正——
   不要把条目列成清单问用户、不要留待确认。估值的依据在修正说明里简短标注即可
   （如「伏特加 1 个 ≈ 一瓶 500ml ≈ 500g」「某进口香料 1 包按常见 50g 包装估」）。
   宁可给一个带依据的合理估值，也不要停下来等用户——这个任务的目标是一次性把
   脏数据清干净。

# 输出格式约束
- 每条写操作 SQL 单独一个 ```sql``` 围栏块，一条一块，不要把多条 UPDATE 塞进
  同一代码块（系统逐块提取判级，混在一起会影响审批粒度）。
- SELECT 查询也用 ```sql``` 块包裹便于阅读，但不会被执行（你需通过 db_read 工具
  实际执行查询）。
- 修正前后给出简短结论：本轮处理了 N 条、修正了哪几类食材。所有条目都要自行决策
  修正完毕，不留待用户确认的尾巴。
"""


TASK_TEMPLATES: dict[str, dict] = {
    "fill_piece_weight": {
        "title": "补单位质量（自定义单位对应克数）",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _FILL_PIECE_WEIGHT_PROMPT,
    },
    # ----------------------------------------------------------------- #
    # 阶段 2 占位（本 Task 不实现 prompt，仅留 key 注明规划）：
    # - "fill_density": 补食材密度字段
    # - "usda_translate": USDA 营养素匹配的食材名翻译
    # ----------------------------------------------------------------- #
}


def get_template(task_type: str) -> dict:
    """返回模板 dict（含 title/prompt/allowed_tools）。

    Args:
        task_type: 任务类型键（如 ``fill_piece_weight``）。

    Returns:
        模板 dict，至少含 ``title`` / ``prompt`` / ``allowed_tools``。

    Raises:
        KeyError: 未知 task_type。
    """
    if task_type not in TASK_TEMPLATES:
        raise KeyError(f"未知任务类型: {task_type}")
    return TASK_TEMPLATES[task_type]


def list_task_types() -> list[dict]:
    """返回 ``[{task_type, title}]`` 供前端按钮列表用。

    顺序按 TASK_TEMPLATES 的插入序（Python 3.7+ dict 保序）。
    """
    return [{"task_type": k, "title": v["title"]} for k, v in TASK_TEMPLATES.items()]
