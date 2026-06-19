# Agent 维护任务扩展：密度推测 / USDA 食材名翻译 / 营养素翻译

> 状态：设计稿。在 `infer_quantities`（推测模糊量）的 Agent 支持实现之后，将相同模式推广到三个新场景。
> 关联：
> - 已有实现：[FEATURE_Agent推测模糊量.md](./FEATURE_Agent推测模糊量.md)、[PLAN_Agent推测模糊量.md](./PLAN_Agent推测模糊量.md)
> - 阶段 2 原计划：[PLAN_Agent维护任务台_阶段2.md](./PLAN_Agent维护任务台_阶段2.md)
> - Agent 架构总览：[FEATURE_Agent维护任务台.md](./FEATURE_Agent维护任务台.md)
> - USDA 功能：[FEATURE_USDA营养素匹配.md](./FEATURE_USDA营养素匹配.md)
> - 之前遗留的密度单位坑：详见 [VOLUME_MASS_CONVERSION_1000X_BUG.md](./VOLUME_MASS_CONVERSION_1000X_BUG.md)

---

## 变更概述

在 `backend/app/services/agent/task_templates.py` 增补三个 Agent 维护任务模板（`infer_densities` / `usda_translate` / `unmapped_nutrient_translate`），同时在 `RecipeImportView` + `UsdaDataView` 的基础上新建统一「数据维护中心」页面，将菜谱导入和 USDA 数据配置的操作入口与任务记录合并管理。

**不改的模块：** Runner / 受控 MCP / sql_guard / 审批 / SSE 流式 / 会话持久化 / AgentTaskConsole——全部复用已有架构。前端按钮由 `list_task_types` 动态拉取，新增模板即自动出现在 Agent 台左侧任务列表；此处页面路由层建新的操作入口，与 Agent 台独立。

---

## 页面架构：数据维护中心

### 路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/admin/data-maintenance` | `DataMaintenanceView.vue` | **新建**——统一操作入口 + 统一任务列表 |
| `/admin/recipe-import` | — | 重定向到 `/admin/data-maintenance` |
| `/admin/usda` | `UsdaDataView.vue` | **保留**——仅保留 USDA 统计数据查看和原始数据浏览，移除翻译操作按钮 |

### 侧边栏

左侧导航菜单：`菜谱导入管理` → 改为 `数据维护中心`，跳转 `/admin/data-maintenance`。

### 页面布局

```
┌─ 数据维护中心 ────────────────────────────────┐
│                                                │
│  ─── 导入数据 ─────────────────                │
│  [从 Git 仓库导入] [从本地路径导入] [上传 ZIP]   │
│                                                │
│  ─── AI 维护 ────────────────────               │
│  AI 推断后端 [▼ claude_code]                    │
│  翻译后端     [▼ openai]                        │
│  □ 强制重新处理全部                             │
│  [推测模糊量] [推测密度] [食材名翻译] [营养素翻译] │
│                                                │
│  ─── USDA 数据管理 ─────────────               │
│  总食材 7,793 | 总营养素 89,201 | 已映射 67%     │
│  [下载 USDA 数据] [上传 ZIP]                    │
│                                                │
│  ─── 未映射营养素（可折叠） ───                  │
│  MUFA  PUFA  12:1  alpha-tocopherol …          │
│                                                │
│  ─── 统一任务列表 ──────────────                 │
│  🟢 Agent 密度推测    2026-06-19 12:35          │
│  🔵 Git 仓库导入      2026-06-19 11:20          │
│  🟠 AI 食材名翻译     2026-06-18 昨天            │
│  ...                                           │
└────────────────────────────────────────────────┘
```

### 两个选择器的行为

| 选择器 | 覆盖按钮 | 可用后端来源 |
|--------|---------|-------------|
| **AI 推断后端** | 推测模糊量、推测密度、营养素翻译 | `translation_config.ai.providers`（仅 AI 类） |
| **翻译后端** | 食材名翻译 | `translation_config.ai + machine.providers`（AI + 机翻） |

**默认值：** 两个选择器各自取对应列表的第一个启用后端；如果 `claude_code` 在 AI 列表中启用且为首位，AI 推断后端默认为 `claude_code`。

### 双路径模式

每个按钮的逻辑（以推测密度为例）：

```typescript
async function inferDensities() {
  const provider = aiInferProvider.value  // 或 translateProvider.value
  if (provider === 'claude_code') {
    // Agent 路径
    const { session_id } = await createSession('infer_densities')
    agentTasks.value.unshift({ session_id, task_type: 'infer_densities', ... })
    startAgentPolling(session_id)
  } else {
    // 旧 API 路径
    const taskId = await startTask('/import/ai-infer/densities', {
      params: { force, provider },
    })
  }
}
```

- `provider === 'claude_code'` → 创建 Agent 会话（任务出现在统一列表 → 点击跳转 AgentTaskConsole）
- 其他 provider → 调用现有 API（走原 `TranslateTask` / `TranslateNutrientsTask` / `AIInferrer` 后台任务）

---

## Feature 1: 推测密度（infer_densities）

### 后端变更

#### `task_templates.py` 新增模板

在 `TASK_TEMPLATES` 字典追加：

```python
"infer_densities": {
    "title": "推测密度（体积↔质量换算）",
    "allowed_tools": list(_READ_ONLY_TOOLS),
    "prompt": _INFER_DENSITIES_PROMPT,
}
```

#### `_INFER_DENSITIES_PROMPT` 要点

**角色：** 食材密度维护助手。

**目标表：** `entity_densities`（entity_type='ingredient'）。**不要碰 `ingredients.density`**（旧字段，已废弃）。

**单位：** 所有输出密度值以 **kg/m³** 为单位（水=1000）。prompt 中反复强调不给出 g/cm³ 的数值对照，防止 Agent 混淆。

**摸底查询：**
```sql
SELECT i.id, i.name, ed.density
FROM ingredients i
LEFT JOIN entity_densities ed ON ed.entity_type='ingredient' AND ed.entity_id=i.id AND ed.condition IS NULL
WHERE i.is_active = 1 AND ed.id IS NULL;
```

**跳过的食材：** 气体、叶片状调味料（八角、香叶等密度无意义）、混合物复合调味料——不强行造数。

**常识参考表（kg/m³）：**
| 食材 | 密度 kg/m³ | confidence |
|------|-----------|------------|
| 水 | 1000 | 1.0 |
| 食用油 | ~920 | 0.9 |
| 蜂蜜 | ~1420 | 0.9 |
| 面粉（松散） | ~550 | 0.8 |
| 白砂糖 | ~850 | 0.9 |
| 牛奶 | ~1030 | 0.9 |
| 盐（颗粒） | ~1200 | 0.8 |
| 大米 | ~850 | 0.9 |
| 坚果（整粒） | ~600-700 | 0.7 |

**INSERT 守卫：**
```sql
INSERT INTO entity_densities (entity_type, entity_id, density, temperature, condition, source, confidence, created_at, updated_at)
SELECT 'ingredient', :id, :density, 20.0, NULL, 'agent', :confidence, datetime('now'), datetime('now')
WHERE NOT EXISTS (
  SELECT 1 FROM entity_densities
  WHERE entity_type='ingredient' AND entity_id=:id AND condition IS NULL
);
```
- 带 `WHERE NOT EXISTS` 防重
- `source='agent'` 标记
- 每批输出 20-30 条 INSERT 后进行一次复核

#### 旧 `inferrer.py` 修复

`infer_densities` 方法的写入目标从 `Ingredient.density`（g/cm³，已废弃）改为 `EntityDensity` 模型（kg/m³）：

```python
from app.models.entity_density import EntityDensity

# AI 返回的 JSON 仍为 g/cm³ 格式（兼容现有消费方）
# 后端自动 * 1000 → kg/m³
density_g_cm3 = parsed.get("density_g_per_cm3")
if density_g_cm3 is not None:
    existing = db.query(EntityDensity).filter(
        EntityDensity.entity_type == 'ingredient',
        EntityDensity.entity_id == ingredient.id,
        EntityDensity.condition.is_(None),
    ).first()
    if not existing:
        ed = EntityDensity(
            entity_type='ingredient',
            entity_id=ingredient.id,
            density=round(density_g_cm3 * 1000, 6),
            temperature=20.0,
            source='ai_inferrer',
            confidence=0.8,
        )
        db.add(ed)
```

### 前端变更

`DataMaintenanceView.vue` 中：

```typescript
async function inferDensities() {
  submitting.aiDensities = true
  try {
    const provider = aiInferProvider.value
    if (provider === 'claude_code') {
      const { session_id } = await createSession('infer_densities', aiForce.value)
      agentTasks.value.unshift({
        session_id, task_type: 'infer_densities',
        label: 'Agent 密度推测', status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      const taskId = await startTask('/import/ai-infer/densities', {
        params: { force: aiForce.value, provider },
      })
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '密度推测任务启动失败'
  }
  submitting.aiDensities = false
}
```

---

## Feature 2: USDA 食材名翻译（usda_translate）

### 后端变更

**模板注册：** 在 `TASK_TEMPLATES` 追加 `usda_translate`，title 为「USDA 食材名翻译」。

**prompt 要点：**

1. **摸底：** `SELECT translate_status, COUNT(*) FROM usda_foods GROUP BY translate_status`
   - 空表或全部 done → 报告结束
2. **翻译规则：** 对齐 `FOOD_TRANSLATION_SYSTEM_PROMPT`：
   - 简洁中文，使用常见食材名
   - 括号补充部位/状态/加工方式
   - 示例：`Chicken breast, boneless, skinless` → `鸡胸肉（去骨去皮）`
3. **批次：** 每轮 50 条，按 `fdc_id` 排序处理最早的 pending 行
4. **守卫：**
   ```sql
   UPDATE usda_foods
   SET description_zh = :translated, translate_status = 'done'
   WHERE fdc_id = :fdc_id AND translate_status = 'pending';
   ```
   - `AND translate_status='pending'` 防止覆盖并发翻译的行
5. **error 行处理：** description 异常（空/乱码）标 `translate_status='error'` 并列出 fdc_id

### 前端变更

`DataMaintenanceView.vue` 中，`translateProvider` 选择翻译后端，点击「食材名翻译」按钮：

```typescript
async function onTranslateFoods() {
  const provider = translateProvider.value
  if (provider === 'claude_code') {
    const { session_id } = await createSession('usda_translate')
    agentTasks.value.unshift({ session_id, task_type: 'usda_translate', label: 'Agent 食材名翻译', ... })
    startAgentPolling(session_id)
  } else {
    await translateUsda(provider)  // 现有 TranslateTask
  }
}
```

---

## Feature 3: 未映射营养素翻译（unmapped_nutrient_translate）

### 后端变更

**模板注册：** 在 `TASK_TEMPLATES` 追加 `unmapped_nutrient_translate`，title 为「未映射营养素名翻译」。

**prompt 要点：**

1. **摸底：**
   ```sql
   SELECT name, COUNT(*) AS cnt
   FROM usda_food_nutrients
   WHERE name_zh IS NULL
   GROUP BY name
   ORDER BY cnt DESC;
   ```
   - 空表或空结果 → 报告结束
2. **对照 172 表已有译文：** 先拉 `SELECT DISTINCT name, name_zh FROM usda_food_nutrients WHERE name_zh IS NOT NULL LIMIT 200`，确保新译与现有用词一致
3. **翻译规则（营养学知识）：**
   - 脂肪酸缩写：`MUFA`→单不饱和脂肪酸、`PUFA`→多不饱和脂肪酸、`SFA`→饱和脂肪酸
   - 脂肪酸记号 `C:D`：`12:1`→12:1 脂肪酸，`12:0`→月桂酸
   - 维生素学名：`Vitamin E (alpha-tocopherol)`→维生素E（α-生育酚）
   - 与 172 表已有条目语义一致的，沿用 172 表的中文用词
4. **守卫：**
   ```sql
   UPDATE usda_food_nutrients
   SET name_zh = :translated
   WHERE name = :original AND name_zh IS NULL;
   ```
   - `AND name_zh IS NULL` 防止覆盖已有翻译
   - 一条 UPDATE 覆盖同名所有行（nutrient name 跨 fdc_id 重复）
5. **单轮上限：** 50 条 distinct name，多轮推进
6. **复核：** 再查 unmapped 计数下降，抽查译文质量

### 前端变更

`DataMaintenanceView.vue` 中，`aiInferProvider` 选择 AI 推断后端，点击「营养素翻译」按钮：

```typescript
async function onTranslateNutrients() {
  const provider = aiInferProvider.value
  if (!unmappedCount.value) { errorMessage.value = '没有未映射的营养素'; return }
  if (provider === 'claude_code') {
    const { session_id } = await createSession('unmapped_nutrient_translate')
    agentTasks.value.unshift({ session_id, task_type: 'unmapped_nutrient_translate', label: 'Agent 营养素翻译', ... })
    startAgentPolling(session_id)
  } else {
    await translateNutrients(provider)  // 现有 TranslateNutrientsTask
  }
}
```

---

## 统一任务列表

完全复用 `RecipeImportView` 中建立的 `mergedTasks` + `agentPolling` + `onMounted` session 恢复模式。

### 关键逻辑

```typescript
// 四种 Agent 任务类型的过滤
const AGENT_TASK_TYPES = [
  'infer_quantities', 'infer_densities',
  'usda_translate', 'unmapped_nutrient_translate',
]

// onMounted 时恢复 Agent 会话
const recent = await listSessions(20)
const relevant = recent.filter((s) => AGENT_TASK_TYPES.includes(s.task_type))
for (const s of relevant) {
  if (!agentTasks.value.find((t) => t.session_id === s.id)) {
    agentTasks.value.push({
      session_id: s.id,
      task_type: s.task_type,
      label: TASK_LABELS[s.task_type],
      status: s.status === 'completed' ? 'success' : s.status,
      created_at: s.created_at || new Date().toISOString(),
    })
  }
}

// 合并 import 任务 + agent 任务
const mergedTasks = computed(() => {
  const imports = tasks.value.map(t => ({ ...t, _kind: 'import' as const }))
  const agents = agentTasks.value.map(t => ({ ...t, _kind: 'agent' as const }))
  return [...imports, ...agents].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})
```

### 任务标签映射

| task_type | label |
|-----------|-------|
| `infer_quantities` | Agent 模糊量推测 |
| `infer_densities` | Agent 密度推测 |
| `usda_translate` | Agent 食材名翻译 |
| `unmapped_nutrient_translate` | Agent 营养素翻译 |

### 轮询

- 每 3 秒轮询一次运行中的 Agent 会话状态
- 终态（success / completed / failed / cancelled）停止轮询
- 组件销毁时清除所有定时器

---

## 不涉及变更的文件

| 文件 | 原因 |
|------|------|
| `backend/app/services/agent/claude_code_runner.py` | 复用 |
| `backend/app/services/agent/session_runner.py` | 复用（多轮循环） |
| `backend/app/services/agent/sql_guard.py` | 复用（INSERT ... WHERE NOT EXISTS 已在 infer_quantities 测试） |
| `backend/app/services/agent/sql_extractor.py` | 复用 |
| `backend/app/services/agent/controlled_db_mcp.py` | 复用（只读 MCP 已有 list_tables / describe / db_read） |
| `backend/app/api/agent_api.py` | 复用（动态读取 TASK_TEMPLATES） |
| `backend/app/schemas/agent.py` | 复用 |
| `frontend/src/views/admin/AgentTaskConsole.vue` | 复用（已有 ?session_id= 参数加载） |
| `frontend/src/composables/useAgentSession.ts` | 复用 |
| `frontend/src/components/agent/*` | 复用（气泡/审批卡） |

---

## 涉及变更的文件

| 文件 | 操作 | 变更内容 |
|------|------|---------|
| `backend/app/services/agent/task_templates.py` | 修改 | 新增 3 个 prompt 常量 + 3 条 TASK_TEMPLATES 条目 |
| `backend/app/services/importer/ai_inference/inferrer.py` | 修改 | `infer_densities` 写入目标改为 `EntityDensity` + 自动单位转换 |
| `frontend/src/views/admin/DataMaintenanceView.vue` | **新建** | 统一数据维护中心页面 |
| `frontend/src/router/index.ts` | 修改 | 新增 `/admin/data-maintenance` 路由；`/admin/recipe-import` 重定向 |
| `frontend/src/views/admin/RecipeImportView.vue` | 删除/重定向 | 页面改为跳转数据维护中心 |
| `frontend/src/views/admin/UsdaDataView.vue` | 修改 | 移除翻译操作按钮，保留统计数据查看 |
| 侧边栏菜单配置 | 修改 | `菜谱导入管理` → `数据维护中心` |

---

## 实施步骤

### Step 1: 新建 DataMaintenanceView.vue
1. 从现有 RecipeImportView.vue 复制为基础
2. 修改布局为三区块（导入数据 / AI 维护 / USDA 数据 + 统一任务列表）
3. 添加两个选择器（AI 推断后端 + 翻译后端）
4. 将四个 Agent 按钮的双路径逻辑整合
5. 移除旧 RecipeImportView 中的 USDA 无关代码

### Step 2: 注册路由与侧边栏
1. 新增 `/admin/data-maintenance` → DataMaintenanceView
2. `/admin/recipe-import` → redirect 到 `/admin/data-maintenance`
3. 侧边栏改名

### Step 3: task_templates.py 新增 3 个模板
1. 编写 `_INFER_DENSITIES_PROMPT`
2. 编写 `_USDA_TRANSLATE_PROMPT`
3. 编写 `_UNMAPPED_NUTRIENT_TRANSLATE_PROMPT`
4. 在 TASK_TEMPLATES 注册三条

### Step 4: 修复 inferrer.py 的密度写入目标
1. `infer_densities` 从写 `Ingredient.density` 改为写 `EntityDensity` 模型
2. 写入时 `g/cm³ * 1000 → kg/m³`
3. 带 `WHERE NOT EXISTS` 查重

### Step 5: UsdaDataView.vue 移除翻译操作
1. 移除翻译按钮和相关的 provider 选择
2. 保留统计数据、未映射营养素列表
3. 增加提示「操作入口已迁至数据维护中心」

### Step 6: 端到端验证
1. 确认 `GET /api/v1/agent/task-types` 返回四个模板
2. 确认四个 Agent 按钮能创建会话
3. 确认统一任务列表显示、刷新、跳转正常
4. 确认旧 API 路径（非 claude_code）仍然可用
5. 确认前端构建通过

---

## 风险与注意事项

### 密度单位坑（最高优先）
`entity_densities.density` 为 kg/m³（水=1000），`Ingredient.density` 为 g/cm³（水=1.0）。prompt 写死 kg/m³；旧 `inferrer.py` 修复时做自动转换。

### USDA 数据未就绪
两个 USDA 模板摸底发现空表会直接报告结束，不作为错误处理。验收前需先确认 `GET /api/v1/admin/usda/statistics` 的 total > 0。

### 172 表复用
Agent 不读 Python 源码，通过 `SELECT DISTINCT name, name_zh FROM usda_food_nutrients WHERE name_zh IS NOT NULL` 从数据库拉取已有译文风格参考。prompt 中强调「与已有译文用词一致」。

### sql_guard 对 INSERT ... WHERE NOT EXISTS 的判级
需在测试时验证。若被判为 dangerous（需要审批），则 prompt 改为「SELECT 探针 + 普通 INSERT」两步走。

### Agent 单轮 SQL 块数量上限
建议 ≤ 50 条/轮，多轮推进。与 `fill_piece_weight` 和 `infer_quantities` 的实践一致。
