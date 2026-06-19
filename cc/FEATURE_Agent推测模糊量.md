# Agent 推测模糊量

## 概述

将「菜谱导入管理」页面的「推测模糊量」按钮从旧的 `AIInferrer` 逐组串行推测方式，改为调用新增的 Agent 架构进行批量推测。Agent 通过受控 MCP 读库摸底 → 输出批量 UPDATE SQL → `sql_guard` 判定执行，一次性处理所有脏数据。

## 现状

- **旧方式**：「推测模糊量」按钮 → `POST /import/ai-infer/quantities` → `AIInferrer.infer_fuzzy_quantities()` → 按 `(ingredient_id, unit_id)` 分组逐组串行调用 AI，每组一次 → 增量提交
- **Agent 架构**：已有 `ClaudeCodeRunner`（subprocess claude code CLI）+ 受控只读 MCP + `sql_extractor` + `sql_guard` + SSE 实时流 + `AgentTaskConsole` 前端
- **已注册任务**：仅 `fill_piece_weight`（处理 `entity_unit_overrides.weight_per_unit`），`infer_quantities` 和 `infer_densities` 仅在模型注释和设计文档中提及，未注册

## 设计

### 工作流

```
用户点击「推测模糊量」
    ↓
POST /api/v1/agent/sessions { task_type: "infer_quantities" }
    ↓ 返回 { session_id }
    ↓
RecipeImportView 任务列表出现新条目「Agent 模糊量推测」
    ↓ 轮询 GET /api/v1/agent/sessions/{sid} 看 status
    ↓
Agent 后台：摸底 → 诊断 → 输出批量 UPDATE SQL → 自动执行
    ↓
用户点击条目 → router.push('/admin/agent-console?session_id=xxx')
             → AgentTaskConsole 自动加载 + SSE 实时流
```

### 后端变更

#### `backend/app/services/agent/task_templates.py`

在 `TASK_TEMPLATES` 中新增 `infer_quantities` 条目，复用现有 prompt 模板结构。

**Agent 目标数据表：**

| 表 | 场景 | 目标字段 |
|---|---|---|
| `ingredients` | 计数单位（unit_system='count'）且 `piece_weight` 为 NULL 或占位值 100 | 推算合理 `piece_weight` + 标记 `ai_inferred = TRUE` |
| `recipe_ingredients` | `quantity` 为 NULL 且 `quantity_range` 为 NULL，或 `original_quantity` 为「适量/少许/少量」 | 推算合理 `quantity_range` + 标记 `ai_inferred = TRUE` |

**Agent 工作流（对齐 `fill_piece_weight` 模式）：**

1. **摸底**：受控 MCP 执行 SELECT 聚合统计，查清 `recipe_ingredients` + `ingredients` + `units` 三表 JOIN 下的缺失分布
2. **诊断**：按 `(ingredient_name, unit_name)` 分组，结合食材常识判断合理值
3. **修正**：输出批量 UPDATE SQL，每条带双重守卫（`WHERE id IN (...) AND (piece_weight IS NULL OR piece_weight = 100)`）
4. **复核**：执行后再次 SELECT 确认改动行数

**不涉及的变更：**
- 无需改数据模型、API 路由、`controlled_db_mcp`（已有 `list_tables` + `db_read` 可覆盖所有表的 SELECT）
- 旧的 `POST /import/ai-infer/quantities` 端点保留不动（兼容旧任务记录查看）
- 旧的 `inferrer.py` 文件保留不动

### 前端变更

#### `frontend/src/views/admin/RecipeImportView.vue`

**① 新增 agent 任务跟踪**

组件内新增 `agentTasks` ref 数组：
```typescript
interface AgentTaskBrief {
  session_id: number
  task_type: string
  label: string
  status: 'pending' | 'running' | 'success' | 'failed'
  created_at: string
}
```

轮询 agent 会话状态：`GET /api/v1/agent/sessions/{id}` → 取 `status` 字段

**② 按钮逻辑改造**

```typescript
// 改为调用 Agent API
import { createSession } from '@/api/agent'

async function inferQuantities() {
  submitting.aiQuantities = true
  try {
    const { session_id } = await createSession('infer_quantities')
    agentTasks.value.unshift({
      session_id,
      task_type: 'infer_quantities',
      label: 'Agent 模糊量推测',
      status: 'pending',
      created_at: new Date().toISOString(),
    })
    startAgentPolling(session_id)
  } catch {
    errorMessage.value = 'Agent 模糊量推测任务启动失败'
  }
  submitting.aiQuantities = false
}
```

**③ 任务列表合并**

```typescript
const mergedTasks = computed(() => {
  const importTasks = tasks.value.map(t => ({ ...t, _kind: 'import' as const }))
  const agentItems = agentTasks.value.map(t => ({ ...t, _kind: 'agent' as const }))
  return [...importTasks, ...agentItems].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})
```

模板中 `v-for="t in mergedTasks"`，区分渲染和点击行为：
- `_kind === 'agent'` → 显示状态标签 + 转圈，点击跳转 `router.push('/admin/agent-console?session_id=' + t.session_id)`
- `_kind === 'import'` → 保持原有进度条/统计/点击行为（当前无点击跳转）

**④ 密度按钮暂不动**

`inferDensities` 按钮保持原逻辑，留后续阶段处理。

## 不涉及变更的文件

- `AgentTaskConsole.vue`：无改动，已支持 `?session_id=` 参数自动加载
- `useImportTask.ts` composable：无改动
- `agent_api.py`、`agent.ts` API 客户端：无改动
- `inferrer.py`：保留不动（旧任务记录兼容）
