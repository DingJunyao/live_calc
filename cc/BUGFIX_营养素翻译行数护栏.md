# 修复：未映射营养素翻译被 100 行护栏误伤

## 症状

USDA 维护页触发「未映射营养素名翻译」（provider=openai 兼容），Agent 提示
「待审批后执行上述 UPDATE，再到下一步复核」，会话卡在 `running`，`name_zh`
实际未写入。

## 根因

不是审批问题，是 `run_agent_loop` 的 **safe_row_threshold 默认 100** 护栏误伤。

链路：

1. 老路径 `nutrient_task.py` 用 `unattended=True`，未传 `safe_row_threshold`，吃默认 100。
2. Agent 输出 `UPDATE usda_food_nutrients SET name_zh=? WHERE name=? AND name_zh IS NULL`
   —— 带 WHERE，sql_guard 判 **safe**。
3. 但单个营养素名跨 fdc_id 重复上万行，`rowcount > 100` 触发 `_handle_safe_sql`
   的 D15 护栏（[`session_runner.py:748`](../backend/app/services/agent/session_runner.py)）→
   回滚 → 转 dangerous → unattended 模式**跳过**（不执行，推 `sql_skipped` SSE）。
4. Agent 发现「100 行限制」，被迫 `WHERE id IN (SELECT ... LIMIT 100)` 分批，
   甚至试 `WITH batch AS (...) UPDATE`（被 sql_guard 当 CTE 写操作再判 dangerous 跳过），
   最终卡死烧 token。所谓「待审批」是 Agent 自己的措辞——它知道超 100 行过不了。

## 数据依据（实测）

| 指标 | 值 |
|---|---|
| `usda_food_nutrients` 总行数 | 649939 |
| distinct name 数 | 246 |
| 单名最大重复（全表） | 15600 |
| 当前未译单名最大 `SFA 16:0` | 6398 |

## 修复

`backend/app/services/translate/nutrient_task.py`：新增模块常量
`_SAFE_ROW_THRESHOLD = 50000`，传给 `run_agent_loop(safe_row_threshold=...)`。

- 放行单名批量更新（最大 15600 < 50000，一次跑完不再分批）；
- 仍兜底拦截无 WHERE 的全表误更新（649939 > 50000 → 转 dangerous → unattended 跳过）。

任务台（attended）路径不动——仍用默认 100，危险大批量写该走人工审批。

## 善后

- **卡住的旧会话**（如 id=9，`status=running` 且占 SQLite 写锁导致间歇 `SQLITE_BUSY`）：
  重启后端（开发者已开自动重载）即清掉后台线程；DB 里残留的 `running` 脏状态可在
  任务台点取消（`cancel_session` 置 `cancelled`）或忽略，不影响新任务。
- **其余三条老路径已一并加固**（同根因，预防性修复）：
  - `translate/task.py`（食材翻译，`usda_foods` 8068 行）→ `_SAFE_ROW_THRESHOLD = 5000`；
  - `inferrer.infer_fuzzy_quantities`（`recipe_ingredients` 3470 / `ingredients` 638）+
    `infer_densities`（`entity_densities` 682）→ 共用 `_SAFE_ROW_THRESHOLD = 5000`。
  - 取值依据：5000 覆盖各表合理批量；sql_guard「无 WHERE 判 dangerous」已挡裸全表更新，
    本阈值补「WHERE 过宽」场景（如误用 `translate_status='pending'` 一次 8068 行 → 转
    dangerous 跳过，提示 Agent 回到按 `fdc_id` 的正轨）。营养素用 50000 是特例
    （`usda_food_nutrients` 65 万行 + 单名上万重复）。

## 续修：Agent 误报「请审批后执行」（prompt 模板缺陷）

阈值修复上线后实测（session 10，50000 阈值）：48 条 UPDATE **全部 `auto_executed`、
`pending=0`**，营养素翻译实际成功。但 Agent 在总结正文里仍说「请主后端审批后执行以上
47 条 UPDATE」，误导用户以为要手动审批——实际系统早已执行完毕。

根因：`task_templates.py` 的 `_UNMAPPED_NUTRIENT_TRANSLATE_PROMPT`「写操作」段**漏写**
了其余四个模板都有的「安全 SQL（带 WHERE 的 UPDATE）自动执行；危险 SQL 才审批」说明，
Agent 不知晓自动执行机制，按通用认知多嘴「请审批」。

修复：补全该模板的写操作判定说明，并显式约束——「UPDATE 带 `WHERE name=? AND name_zh
IS NULL` 守卫会被系统自动执行，**不要在正文里说『请审批后执行』『待审批』**」。
