# Agent 推测模糊量 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将「菜谱导入管理」页面的「推测模糊量」按钮从旧 `AIInferrer` 逐组串行方式改为 Agent 批量推测。

**Architecture:** 后端在 `task_templates.py` 新增 `infer_quantities` 任务模板，复用现有 `ClaudeCodeRunner` + 受控 MCP + `sql_guard` 管线；前端 `RecipeImportView.vue` 按钮调用 Agent API 创建会话 → 显示在任务列表 → 点击跳转 AgentTaskConsole。

**Tech Stack:** Python/FastAPI + Vue 3/TypeScript + Claude Code CLI (Agent)

---
## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/services/agent/task_templates.py` | 修改 | 新增 `infer_quantities` 模板 + prompt |
| `frontend/src/views/admin/RecipeImportView.vue` | 修改 | 按钮改调 Agent API + agent 任务跟踪 + 列表合并 |

---

### Task 1: 后端 — 新增 `infer_quantities` 任务模板

**Files:**
- Modify: `backend/app/services/agent/task_templates.py`

**表结构参考：**
- `recipe_ingredients`: id, recipe_id, ingredient_id, quantity, quantity_range(JSON), unit_id, original_quantity(JSON), ai_inferred
- `ingredients`: id, name, density, piece_weight(Numeric), piece_weight_unit_id, ai_inferred, is_active
- `units`: id, name, abbreviation, unit_type, unit_system

- [ ] **Step 1: 在 `TASK_TEMPLATES` 中新增 `infer_quantities` 条目**

在 `TASK_TEMPLATES` dict 末尾、在占位注释之前插入新条目：

```python
    "infer_quantities": {
        "title": "推测模糊量（菜谱原料用量推理）",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _INFER_QUANTITIES_PROMPT,
    },
```

同时新增顶层 prompt 常量 `_INFER_QUANTITIES_PROMPT`，内容如下。

- [ ] **Step 2: 编写 `_INFER_QUANTITIES_PROMPT`**

```python
_INFER_QUANTITIES_PROMPT = """你是「生计」应用的菜谱数据维护助手，专门负责推断菜谱原料的模糊用量。

# 任务目标
处理 ``recipe_ingredients`` 表中模糊/缺失的用量数据，具体包括：
1. **计数单位缺少 piece_weight**：单位是计数单位（unit_system='count'）但对应原料
   ``ingredients.piece_weight`` 为空或 =100（历史占位值），需要推算每个单位多少克。
2. **用量为空或模糊文本**：``quantity IS NULL`` 且 ``quantity_range IS NULL``，
   或 ``original_quantity`` 包含「适量/少许/少量」，需要推算合理的默认用量区间。

涉及三张表：
- ``recipe_ingredients``：菜谱-原料关联表（主表）
- ``ingredients``：原料表（含 piece_weight）
- ``units``：单位表（含 unit_system）

# 工具说明（重要）
你只有以下三个**只读**工具可用：
- ``mcp__controlled_db__db_read``：执行 SELECT 查询。
- ``mcp__controlled_db__describe``：查看表结构。
- ``mcp__controlled_db__list_tables``：列出所有表。

**你没有任何写工具**。需要写库时，**在你的回复正文里用 ```sql``` 代码块输出 SQL**——
系统的 sql_extractor 会自动提取，sql_guard 判定：
- 安全 SQL（INSERT / 带 WHERE 的 UPDATE）自动执行；
- 危险 SQL（DELETE / 无 WHERE 的 UPDATE / DROP 等）会生成审批记录交给管理员审批。

不要试图调用不存在的写工具，也不要把 SQL 写在普通段落里（必须用 ```sql``` 围栏）。

# 工作流程
按以下步骤推进，每一步先观察再决策：

## 第一步：摸底统计

用 db_read 执行以下查询，了解需要处理的脏数据规模：

1. **计数单位缺失 piece_weight 的原料统计**：
   ```sql
   SELECT i.id AS ingredient_id, i.name AS ingredient_name,
          u.name AS unit_name, u.unit_system,
          COUNT(DISTINCT ri.id) AS recipe_count,
          i.piece_weight, i.ai_inferred
   FROM recipe_ingredients ri
   JOIN ingredients i ON i.id = ri.ingredient_id
   JOIN units u ON u.id = ri.unit_id
   WHERE u.unit_system = 'count'
     AND (i.piece_weight IS NULL OR i.piece_weight = 100)
     AND i.is_active = 1
   GROUP BY i.id
   ORDER BY recipe_count DESC;
   ```

2. **用量为空/模糊的条目统计**：
   ```sql
   SELECT i.id AS ingredient_id, i.name AS ingredient_name,
          COUNT(DISTINCT ri.id) AS recipe_count,
          ri.quantity, ri.quantity_range, ri.original_quantity,
          ri.ai_inferred
   FROM recipe_ingredients ri
   JOIN ingredients i ON i.id = ri.ingredient_id
   WHERE (ri.quantity IS NULL AND ri.quantity_range IS NULL)
      OR ri.original_quantity IN ('适量', '少许', '少量')
   GROUP BY i.id
   ORDER BY recipe_count DESC;
   ```

3. （可选）拉取具体明细确认上下文，如：
   ```sql
   SELECT ri.id, r.name AS recipe_name, i.name AS ingredient_name,
          u.name AS unit_name, ri.quantity, ri.quantity_range,
          ri.original_quantity, i.piece_weight
   FROM recipe_ingredients ri
   JOIN recipes r ON r.id = ri.recipe_id
   JOIN ingredients i ON i.id = ri.ingredient_id
   LEFT JOIN units u ON u.id = ri.unit_id
   WHERE ...
   ORDER BY i.name;
   ```

## 第二步：诊断与估算

对每条需要处理的数据，结合食材常识推断合理值。

### 计数单位 piece_weight 参考（常见食材每个/每颗的典型克数）：
- 鸡蛋 1 个 ≈ 55g（带壳，中号）
- 大蒜 1 瓣 ≈ 5g
- 八角 1 颗 ≈ 1-2g
- 花椒 1 粒 ≈ 0.02g
- 干辣椒 1 个 ≈ 2-3g
- 生姜 1 片 ≈ 3-5g
- 葱 1 根 ≈ 15-20g
- 土豆 1 个 ≈ 150-200g
- 番茄 1 个 ≈ 100-150g
- 洋葱 1 个 ≈ 150-200g
- 苹果 1 个 ≈ 150-200g
- 香蕉 1 根 ≈ 100-120g
- 柠檬 1 个 ≈ 80-100g
- 青椒 1 个 ≈ 80-120g
- 猪肉 1 份 ≈ 200-250g（菜谱常见一份量）
- 鸡肉 1 份 ≈ 150-200g
- 牛肉 1 份 ≈ 150-200g

其他食材按以下原则估计：
- 常见的单个水果蔬菜：参考同类大小
- 干货/调味料：按常见包装/使用习惯估算
- 不熟悉的食材：搜索同类食材，给出合理估值并标注依据
- **对所有条目必须给出估值，不能跳过或留待用户确认**

### 模糊用量 quantity_range 参考（「适量」时的默认用量）：
- 常见调味料（盐、糖、生抽等）适量 ≈ 5-10g
- 油类适量 ≈ 10-15g
- 香料类（花椒、八角等）适量 ≈ 1-3g
- 水/高汤适量 ≈ 100-200g
- 蔬菜类适量 ≈ 50-100g
- 肉类适量 ≈ 100-200g

如果某食材既有 piece_weight 推断又有 quantity_range 推断，一并处理。

## 第三步：输出 SQL

按以下规则输出 UPDATE SQL：

### 更新 ingredients.piece_weight
```sql
UPDATE ingredients
SET piece_weight = <新值>, ai_inferred = 1
WHERE id IN (<id1>, <id2>, ...)
  AND (piece_weight IS NULL OR piece_weight = 100);
```

### 更新 recipe_ingredients.quantity_range（用于原"适量"等模糊条目）
```sql
UPDATE recipe_ingredients
SET quantity_range = '{"min": <最小值>, "max": <最大值>}', ai_inferred = 1
WHERE id IN (<ri_id1>, <ri_id2>, ...)
  AND quantity IS NULL
  AND (quantity_range IS NULL OR json_extract(quantity_range, '$.min') = 0);
```

**核心规则：**
- 每条 UPDATE 单独一个 ```sql``` 围栏块——不要合并多条 UPDATE 到一个块
- 必须带双重守卫：`WHERE id IN (...)` + 原值判断
- 将所有同类更新合并成少量几条批量 UPDATE（按合理值分组），不要逐条单独 UPDATE
- 标记 `ai_inferred = 1`（SQLite 用 1 表示 TRUE）

## 第四步：复核

执行后用 db_read 重新查询确认：
```sql
SELECT COUNT(*) AS remaining
FROM recipe_ingredients ri
JOIN ingredients i ON i.id = ri.ingredient_id
LEFT JOIN units u ON u.id = ri.unit_id
WHERE ...
  AND ri.ai_inferred = 0;
```

确认剩余条数为 0 或合理可忽略的少数。

# 输出格式约束
- 每条写操作 SQL 单独一个 ```sql``` 围栏块。
- SELECT 查询也用 ```sql``` 块包裹（但通过 db_read 工具执行，不会被作为写操作处理）。
- 修正前后给出简短结论：本轮处理了 N 条、修正了哪几类食材/用量。

# 重要
- **全部自己决策，不问用户。** 即使是不常见的食材，也要基于常识/典型规格给出合理的估计值直接修正——不要把条目列成清单问用户。宁可给一个带依据的合理估值，也不要停下来等用户。
- 如果某条数据看起来已经合理（如 piece_weight=50 对鸡蛋是合理的），不要动它。
- 对于 `original_quantity` 包含「适量/少许/少量」之外的文本描述的条目，跳过不处理。
"""
```

- [ ] **Step 3: 确认模板注册正确**

检查 `task_templates.py` 末尾的 `list_task_types()` 函数——它遍历 `TASK_TEMPLATES`，新条目会自动暴露给 `GET /api/v1/agent/task-types`。无需修改此函数。

---

### Task 2: 前端 — RecipeImportView 调用 Agent 并合并任务列表

**Files:**
- Modify: `frontend/src/views/admin/RecipeImportView.vue`

- [ ] **Step 1: 导入 agent API 和 router**

在 `<script setup>` 的 import 块末尾添加：

```typescript
import { createSession } from '@/api/agent'
```

`useRouter` 已经导入了（第 284 行），但确认 `router` 变量可用（第 291 行已有 `const router = useRouter()`）。

- [ ] **Step 2: 新增 `AgentTaskItem` 类型接口和 agent 任务跟踪状态**

在 `<script setup>` 中 `errorMessage` 之后添加：

```typescript
interface AgentTaskItem {
  session_id: number
  task_type: string
  label: string
  status: 'pending' | 'running' | 'success' | 'failed'
  created_at: string
}

const agentTasks = ref<AgentTaskItem[]>([])
const agentPollingMap = new Map<number, ReturnType<typeof setInterval>>()
const agentErrorMap = ref<Record<number, string>>({})
```

- [ ] **Step 3: 新增 agent 会话轮询逻辑**

在 `inferQuantities` 函数之后添加：

```typescript
function startAgentPolling(sessionId: number) {
  if (agentPollingMap.has(sessionId)) return
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/v1/agent/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const idx = agentTasks.value.findIndex(t => t.session_id === sessionId)
      if (idx >= 0) {
        const status = data.status === 'completed' ? 'success' : data.status
        agentTasks.value[idx] = { ...agentTasks.value[idx], status }
        if (data.error) {
          agentErrorMap.value[sessionId] = data.error
        }
      }
      if (data.status === 'success' || data.status === 'completed' || data.status === 'failed') {
        stopAgentPolling(sessionId)
      }
    } catch {
      stopAgentPolling(sessionId)
    }
  }, 3000)
  agentPollingMap.set(sessionId, interval)
}

function stopAgentPolling(sessionId: number) {
  const interval = agentPollingMap.get(sessionId)
  if (interval) {
    clearInterval(interval)
    agentPollingMap.delete(sessionId)
  }
}
```

- [ ] **Step 4: 改造 `inferQuantities` 函数调用 Agent API**

将现有的 `inferQuantities` 函数替换为：

```typescript
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
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || 'Agent 模糊量推测任务启动失败'
  }
  submitting.aiQuantities = false
}
```

- [ ] **Step 5: 移除旧端点对应的 `inferTaskType` 映射**

在 `useImportTask.ts` 中 `inferTaskType` 函数里有 `if (endpoint.includes('quantities')) return 'ai_quantities'` 和 `if (endpoint.includes('densities')) return 'ai_densities'`。现在 `inferQuantities` 不再调用 `startTask` 所以不再经过此函数，无需修改。

- [ ] **Step 6: 添加合并任务列表的 computed 属性**

在 `formatTime` 函数之前添加：

```typescript
interface ImportTaskLike {
  id: number
  task_type: string
  status: string
  progress?: { stage: string; current: number; total: number; message: string }
  stats?: Record<string, number>
  error?: string | null
  created_at: string
  _kind: 'import'
}

interface AgentTaskLike extends AgentTaskItem {
  _kind: 'agent'
}

type MergedTask = ImportTaskLike | AgentTaskLike

const mergedTasks = computed<MergedTask[]>(() => {
  const imports: ImportTaskLike[] = tasks.value.map(t => ({ ...t, _kind: 'import' as const }))
  const agents: AgentTaskLike[] = agentTasks.value.map(t => ({ ...t, _kind: 'agent' as const }))
  return [...imports, ...agents].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
})
```

- [ ] **Step 7: 修改模板任务列表，合并渲染 agent 和 import 条目**

将 `<v-list>` 内容（第 217-273 行）替换为下面内容（注意 `v-for` 遍历 `mergedTasks`，区分 `_kind`）：

```vue
            <v-list v-else>
              <v-list-item
                v-for="t in mergedTasks" :key="t._kind === 'import' ? 'imp-' + t.id : 'agt-' + t.session_id"
                class="mb-2 border rounded"
                :class="t._kind === 'import' ? taskRunningClass(t.status) : ''"
                :style="t._kind === 'agent' ? { cursor: 'pointer' } : {}"
                @click="t._kind === 'agent' ? router.push('/admin/agent-console?session_id=' + t.session_id) : undefined"
              >
                <template #prepend>
                  <v-icon :color="statusColor(t.status)" class="mr-3">
                    {{ statusIcon(t.status) }}
                  </v-icon>
                </template>
                <v-list-item-title class="font-weight-medium">
                  {{ t._kind === 'agent' ? t.label : taskTypeLabel(t.task_type) }}
                  <v-chip :color="statusColor(t.status)" size="x-small" variant="tonal" class="ml-2">
                    {{ statusLabel(t.status) }}
                  </v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>
                  <!-- import 任务：进度条 / 统计 / 错误 -->
                  <template v-if="t._kind === 'import'">
                    <div v-if="t.progress?.stage" class="text-caption mt-1">
                      {{ t.progress.stage }}: {{ t.progress.message }}
                    </div>
                    <div v-if="t.progress?.total > 0" class="mt-1">
                      <v-progress-linear
                        :model-value="Math.round((t.progress.current / t.progress.total) * 100)"
                        height="6" rounded color="primary"
                      />
                      <div class="text-caption text-medium-emphasis mt-1">
                        {{ t.progress.current }} / {{ t.progress.total }}
                        ({{ Math.round((t.progress.current / t.progress.total) * 100) }}%)
                      </div>
                    </div>
                    <div v-if="t.stats && Object.keys(t.stats).length" class="text-caption mt-1">
                      <v-chip v-for="(v, k) in t.stats" :key="k" size="x-small" variant="tonal"
                              class="mr-1 mb-1">{{ k }}: {{ v }}</v-chip>
                    </div>
                    <div v-if="t.error" class="text-caption text-error mt-1">{{ t.error }}</div>
                  </template>
                  <!-- agent 任务：简洁状态 -->
                  <template v-else>
                    <div v-if="agentErrorMap[t.session_id]" class="text-caption text-error mt-1">
                      {{ agentErrorMap[t.session_id] }}
                    </div>
                    <div class="text-caption text-medium-emphasis mt-1">点击查看实时详情</div>
                  </template>
                  <div class="text-caption text-medium-emphasis mt-1">{{ formatTime(t.created_at) }}</div>
                </v-list-item-subtitle>
                <template #append>
                  <v-progress-circular
                    v-if="t.status === 'running' || t.status === 'pending'"
                    indeterminate size="20" width="2" color="primary"
                  />
                </template>
              </v-list-item>
            </v-list>
```

- [ ] **Step 8: 验证前端构建**

在项目根目录运行：

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

确保无 TypeScript 类型错误。

```bash
cd frontend && npx vite build 2>&1 | tail -20
```

确保构建通过。

---

### Task 3: 端到端验证

- [ ] **Step 1: 确认后端启动正常**

后端应该已经热重载，确认新模板注册成功：

```bash
curl -s http://localhost:8000/api/v1/agent/task-types | python -m json.tool
```

预期输出应包含 `{"task_type": "infer_quantities", "title": "推测模糊量（菜谱原料用量推理）"}`。

- [ ] **Step 2: 前端功能验证**
1. 打开菜谱导入管理页 `http://localhost:5173/admin/recipe-import`
2. 点击「推测模糊量」按钮
3. 确认任务列表出现「Agent 模糊量推测」条目，状态为运行中
4. 点击该条目，确认跳转到 Agent 任务台并显示实时 Agent 对话流
5. 确认 Agent 完成任务后状态变为「成功」

- [ ] **Step 3: 记录要点**

将实现要点记录到 `cc/` 目录的摘要文件。
