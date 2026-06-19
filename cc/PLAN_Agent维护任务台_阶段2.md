# Agent 维护任务台 · 阶段 2 实施计划（补密度 / USDA 食材翻译 / 未映射营养素翻译）

> 状态：**计划稿，待以后执行**。复用阶段 1 架构，只读探索已完成，落点/单位/复用点均有代码依据。
> 关联：
> - 设计稿：[FEATURE_Agent维护任务台.md](./FEATURE_Agent维护任务台.md)
> - 阶段 1 计划：[PLAN_Agent维护任务台_阶段1.md](./PLAN_Agent维护任务台_阶段1.md)
> - USDA 功能全貌：[FEATURE_USDA营养素匹配.md](./FEATURE_USDA营养素匹配.md)

**Goal:** 在 `backend/app/services/agent/task_templates.py` 增补三个维护任务模板（`fill_density` / `usda_translate` / `unmapped_nutrient_translate`），让管理员在任务台一键发起 Agent 自主维护。**不改阶段 1 的 Runner / 受控 MCP / sql_guard / 审批 / 流式 / 前端**——前端按钮由 `list_task_types` 动态拉取，加模板即自动出现。

**前提（阶段 1 已就绪）：**
- `agent_sessions` / `agent_messages` / `agent_approvals` 三表、`ClaudeCodeRunner`、受控只读 MCP（`db_read` / `describe` / `list_tables`）、`sql_extractor` + `sql_guard`（safe 自动执行 / dangerous 审批）、SSE 流式、会话持久化均已上线。
- `task_templates.TASK_TEMPLATES` 已为 `fill_piece_weight` 注册一条；阶段 2 三个任务同形追加即可。
- `task_templates.py` 顶部已留阶段 2 占位注释（`fill_density` / `usda_translate`），删除占位、补条目。

---

## ⚠️ 执行前必读：当前数据库实测现状（2026-06-19 探查）

执行者务必先复核这三张表的实时数据量，**这决定三个任务的可行性与优先级**：

| 表 / 字段 | 实测现状 | 含义 |
| --- | --- | --- |
| `entity_densities` | **0 行（空表）** | 补密度任务的落点表当前没有任何数据 |
| `ingredients.density` | 638 条原料，**638 条 density 全为 NULL** | 旧字段（g/mL），新代码已不走此字段 |
| `usda_foods` | **0 行（空表）** | USDA 原始数据尚未下载导入 |
| `usda_food_nutrients` 未映射（`name_zh IS NULL`） | **0 条** | 因 USDA 数据未入库，无营养素可翻译 |

**推论：**
1. **`fill_density` 立刻可做且有价值**——638 条原料缺密度，`entity_densities` 空表正好让 Agent 从零 INSERT（守卫简单：只 INSERT 缺失，无 UPDATE 冲突）。
2. **`usda_translate` / `unmapped_nutrient_translate` 当前无数据可处理**——必须等 USDA 数据下载入库后才有意义。这两个任务模板**可以先注册（占位+prompt 写好），但实测要等 USDA 数据就绪**。

执行者优先做 `fill_density`；后两个模板可同期写入，但端到端验收前先跑 `GET /api/v1/admin/usda/statistics` 确认 `usda_foods.total > 0`。

---

## 共性（三个任务都复用，不重写）

- 都在 `task_templates.py` 的 `TASK_TEMPLATES` 字典追加一条：`{title, prompt, allowed_tools}`，`allowed_tools` 复用模块级 `_READ_ONLY_TOOLS`（`db_read` / `describe` / `list_tables`）。
- 都复用阶段 1 的 Agent loop / 受控只读 MCP / `sql_extractor` + `sql_guard` / 危险写审批 / SSE 流式 / 会话持久化。
- prompt 都遵循阶段 1 定下的五条铁律：
  1. 角色定位 + 任务目标（维护哪张表哪个字段）；
  2. 工具说明（只有三个只读工具，写操作靠 ```sql``` 代码块）；
  3. 工作流程（先 db_read 摸底 → 诊断 → 估值 → 输出 SQL → 复核）；
  4. **守卫**（每条写 SQL 带 `WHERE` 双重限定 + `source='agent'` 审计标记）；
  5. **全自己决策，不问用户**（给带依据的估值，不留待确认尾巴）。
- 前端**无需改动**：`list_task_types()` 动态返回，任务台按钮自动多出三个。

---

## Task 2-1: `fill_density`（补食材密度）

### 落点（探索已确认）

- **主落点：`entity_densities` 表**（`backend/app/models/entity_density.py`），字段：
  - `entity_type`（`'ingredient'` / `'product'`）
  - `entity_id`
  - `density` `Numeric(10,6)` **单位 kg/m³（SI 基准）**
  - `temperature`（参考温度℃，可空）
  - `condition`（状态描述，如「切碎」「压碎」「过筛」）
  - `source`（数据来源 → 标 `'agent'`）
  - `confidence` `Numeric(3,2)` 默认 1.0
  - 唯一约束：`uq_entity_density (entity_type, entity_id, condition)`
- **消费者（为什么补这张表）：** `backend/app/services/unit_conversion_service.py` 的 `UnitConversionService.get_density()` 优先级链——先查 `entity_densities`（按 `confidence` 降序取首条）→ product 回退到关联 ingredient 的密度 → 兜底水 1000 kg/m³。体积↔质量单位换算（如「毫升→克」「杯→克」）完全依赖此表。
- **不要写到 `ingredients.density`**：那是**旧字段**，注释为 g/mL 或 kg/L，`inferrer.py` 的 `infer_densities` 写的就是这个旧字段，单位是 g/cm³（水=1.0），与 `entity_densities` 的 kg/m³（水=1000）**数值差 1000 倍**。新代码（`unit_conversion_service`）只读 `entity_densities`，不读 `ingredients.density`。
- **`IngredientDensity` / `ingredient_densities` 表已 DEPRECATED**（`backend/app/models/ingredient_density.py` 顶部明示），`recipe_service.py:1768` 还有一处旧引用，阶段 2 **不碰**，避免扩大改动面。

### ⚠️ 单位坑（必须在 prompt 里写死）

| 来源 | 单位 | 水的值 |
| --- | --- | --- |
| `entity_densities.density`（**目标**） | **kg/m³** | **1000** |
| `Ingredient.density`（旧字段，inferrer.py 用） | g/mL ≈ kg/L | 1.0 |
| `IngredientDensity.density_value`（DEPRECATED） | 未严格定义 | — |

**prompt 必须明确：所有输出密度值用 kg/m³。** 给 Agent 的常识参考表也要用 kg/m³：

| 食材 | 密度 kg/m³ |
| --- | --- |
| 水 | 1000 |
| 食用油 | ~920 |
| 蜂蜜 | ~1420 |
| 面粉（松散） | ~550 |
| 白砂糖 | ~850 |
| 牛奶 | ~1030 |
| 盐（颗粒） | ~1200 |
| 大米 | ~850 |
| 坚果（整粒） | ~600-700 |

### prompt 要点

1. **摸底**：`db_read` 查 `ingredients` 表（638 条全缺密度），并 LEFT JOIN `entity_densities` 看哪些已有记录（当前空表，预期全缺）。
2. **分类估值**：
   - 液体（油/水/酱/醋/蜂蜜/牛奶）→ 按液体密度常识；
   - 粉状（面粉/糖/盐/淀粉/可可粉）→ 按松散堆密度；
   - 整粒固体（米/豆/坚果）→ 按颗粒堆密度；
   - **气体/叶片状/调味料混合物（如「八角」「香叶」）密度无意义** → 跳过，不强行造数。
3. **INSERT 缺失（关键守卫）**：每条 INSERT 前先确认 `(entity_type='ingredient', entity_id=X, condition IS NULL)` 不存在（空表场景下基本都缺，但守卫仍要写）。模板：
   ```sql
   INSERT INTO entity_densities (entity_type, entity_id, density, temperature, condition, source, confidence, created_at, updated_at)
   SELECT 'ingredient', <id>, <density_kg_m3>, 20.0, NULL, 'agent', 0.8, datetime('now'), datetime('now')
   WHERE NOT EXISTS (
     SELECT 1 FROM entity_densities
     WHERE entity_type='ingredient' AND entity_id=<id> AND condition IS NULL
   );
   ```
   SQLite 用 `INSERT ... WHERE NOT EXISTS`；若 sql_guard 对该语法判级有疑问，回退为「先 SELECT 探针，确认无记录再 INSERT」（Agent 自己分两步）。**待核对：sql_guard 对 `INSERT ... SELECT ... WHERE NOT EXISTS` 的判级**（阶段 1 只验过 UPDATE/DELETE，INSERT 的判定规则需在测试时确认）。
4. **condition 字段**：默认不填（NULL = 常温常态）；若某食材有显著状态差异（如「黄油融化 vs 冷凝」），可输出多条 INSERT 不同 condition。阶段 2 建议先只补常态（condition=NULL），降低复杂度。
5. **confidence**：液体/常见粉状给 0.9（常识明确）；冷门食材给 0.7；估值依据在说明里简短标注。
6. **复核**：INSERT 后 `db_read` 统计 `entity_densities` 行数增长、抽查几条原料的密度合理性。

### 守卫清单

- 只 INSERT `entity_densities`，**不动 `ingredients.density`、不动 `ingredient_densities`**。
- 每条 INSERT 带 `WHERE NOT EXISTS` 双重防重。
- `source='agent'` 标记本次维护来源。
- 不为密度无意义的食材（气体、叶片香料）强行造数——宁缺毋滥。

### 待核对

- [ ] `sql_guard` 对 `INSERT ... SELECT ... WHERE NOT EXISTS` 的判级（safe 自动执行 or dangerous 审批？）。若被判 dangerous，则 prompt 改为「SELECT 探针 + 普通 INSERT」两步走。
- [ ] `entity_densities` 的 `created_at` / `updated_at` 是否有 `server_default`（模型有 `func.now()`，SQLite/MySQL/PG 行为一致确认）。
- [ ] 是否需要 Alembic 迁移：**不需要**（表已存在，只是空）。
- [ ] 是否需要提供 SQL 脚本（CLAUDE.md 要求表结构变动时提供四套 SQL）：**不需要**（无表结构变动）。

---

## Task 2-2: `usda_translate`（USDA 食材名翻译）

### ⚠️ 价值复核：是否真需要 Agent？

**现状（探索已确认）：此任务已有完整后端服务 + API，无需 Agent 也能跑。**

- 现有服务：`backend/app/services/translate/task.py` 的 `TranslateTask`——取 `usda_foods WHERE translate_status='pending'`，按 batch_size=50 调翻译后端（6 选 1：claude_code / openai / anthropic / 百度 / 阿里云 / DeepL），写回 `description_zh` + `translate_status='done'`，进度写 `usda_tasks`。
- 现有 API：`POST /api/v1/admin/usda/translate`（`body: {provider}`）→ 后台任务跑 `TranslateTask`。
- 翻译系统提示：`backend/app/services/translate/base.py` 的 `FOOD_TRANSLATION_SYSTEM_PROMPT`（已是精心调过的食材翻译 prompt）。
- 落点：`usda_foods.description_zh` / `translate_status`。

**判断：Agent 任务在此场景的增量价值有限**——现有 API 已经是「一键批量翻译」，Agent 不会比专用翻译后端更准或更快。Agent 的可能价值仅在于：
1. 翻译后端全部不可用/未配置时的**兜底**（Agent 本身就是 claude code，能直接翻译）；
2. 对翻译质量做**抽检复核**（挑 `translate_status='error'` 或译文可疑的重翻）；
3. 不依赖 `translation_configs` 配置的**独立通道**（管理员没配 OpenAI/百度 key 时也能翻）。

**建议（执行者与开发者确认）：**
- **方案 A（推荐）**：不建独立 Agent 任务，保持现有 API。若要进任务台，可做一个**「USDA 翻译状态巡检」**任务——Agent 只读统计 `pending/error` 数量、抽检可疑译文质量、给出建议，**不直接写翻译**（写翻译交给现有 API）。
- **方案 B**：建 `usda_translate` Agent 任务作为**兜底翻译通道**——Agent 用自身能力翻译 `pending` 行，输出 `UPDATE usda_foods SET description_zh=..., translate_status='done' WHERE id=... AND translate_status='pending'`。

### 若采方案 B，prompt 要点

1. **摸底**：`db_read` 查 `usda_foods` 的 `translate_status` 分布（pending / done / error 计数），拉一批 pending 的 `fdc_id` + `description`。
2. **翻译**：Agent 用 `FOOD_TRANSLATION_SYSTEM_PROMPT` 同款规则（简洁中文 + 括号补部位/状态/加工）直接译，示例对齐 `base.py`。
3. **守卫 UPDATE**：
   ```sql
   UPDATE usda_foods
   SET description_zh='<译文>', translate_status='done'
   WHERE fdc_id=<id> AND translate_status='pending';
   ```
   `AND translate_status='pending'` 防止覆盖已被其它流程（现有 API）翻译过的行。
4. **批次**：建议每轮处理 50-100 条（受 Agent 上下文/SQL 块数限制），不一次性吞全量。
5. **error 行**：单独诊断，若是 description 异常（空/乱码）标 `translate_status='error'` 并在说明里列出，不强行造译文。

### 守卫清单

- 只 UPDATE `usda_foods` 的 `description_zh` / `translate_status`，不动其它表。
- 每条 UPDATE 带 `WHERE fdc_id=... AND translate_status='pending'` 双重限定。
- 不动 `usda_food_nutrients`（那是 Task 2-3 的地盘）。

### 待核对

- [ ] **方案 A vs B 取舍**（开发者决策）——这是本任务是否真要做的 gate。
- [ ] 若 USDA 数据未下载（`usda_foods` 空），本任务无数据可处理——验收前确认 `GET /api/v1/admin/usda/statistics` 的 `total > 0`。
- [ ] Agent 批量 UPDATE 的 SQL 块数量上限（sql_extractor 逐块提取，块太多会拖慢审批流）——建议单轮 ≤ 50 条。

---

## Task 2-3: `unmapped_nutrient_translate`（未映射营养素名翻译）

### 落点与现状（探索已确认）

- **172 条静态映射表**：`backend/app/services/usda/nutrient_mapping.py` 的 `NUTRIENT_TRANSLATIONS` 字典（实测 172 条），`map_nutrient_name(name_en)` 查表（含小写索引 `_LOWER_INDEX`）。**这张表是静态的，导入 USDA 时自动套用，不走 AI。**
- **「未映射营养素」定义**：`usda_food_nutrients.name_zh IS NULL` 的行——即 172 表覆盖不到的 USDA 营养素名（多为脂肪酸具体记号如 `12:1`、维生素学名变体、稀有矿物质）。
- **落点**：`usda_food_nutrients.name_zh`。
- **现有服务**：`backend/app/services/translate/nutrient_task.py` 的 `TranslateNutrientsTask`——取 `DISTINCT name WHERE name_zh IS NULL`，按 batch_size=50 调翻译后端（用 `NUTRIENT_TRANSLATION_SYSTEM_PROMPT`，营养学专用），写回 `name_zh`。
- **现有 API**：`POST /api/v1/admin/usda/translate-nutrients`（`body: {provider}`）+ `GET /api/v1/admin/usda/unmapped-nutrients`（返回未映射 distinct name 清单）。

### ⚠️ 价值复核（同 Task 2-2）

**此任务也已有完整后端服务 + API。** Agent 增量价值同样有限，判断逻辑同上。

**关键区别：营养素名翻译比食材名更需要「知识」**——172 表之所以静态化，正是因为脂肪酸记号（`MUFA`/`PUFA`/`12:1`）、维生素学名（`alpha-tocopherol`）机翻不准，需要营养学专家级判断。Agent（claude code）恰好具备这类知识，**作为兜底翻译通道的价值比 Task 2-2 更高**。

**建议：**
- **方案 A（推荐）**：建 `unmapped_nutrient_translate` Agent 任务作为**兜底 + 复核通道**。Agent 先 `GET` 思路读 `unmapped-nutrients` 清单（或直接 db_read），用自身营养学知识翻译，输出 UPDATE。比 Task 2-2 更值得做，因为：
  1. 不依赖外部翻译后端配置；
  2. Agent 对脂肪酸记号/学名翻译质量可能优于通用机翻；
  3. 可顺便复核现有 `name_zh` 是否有明显错译。
- 也可考虑：Agent 翻译完的成果，**回填到 172 静态表**（扩展 `NUTRIENT_TRANSLATIONS`）——但这会改 Python 源码，超出「Agent 写 SQL」范围，**阶段 2 不做**，仅写 `usda_food_nutrients.name_zh`。

### prompt 要点

1. **摸底**：
   ```sql
   SELECT name, COUNT(*) AS cnt
   FROM usda_food_nutrients
   WHERE name_zh IS NULL
   GROUP BY name
   ORDER BY cnt DESC;
   ```
   拿到未映射 distinct name 清单（当前 0 条，等 USDA 数据入库后才有）。
2. **翻译规则**（对齐 `NUTRIENT_TRANSLATION_SYSTEM_PROMPT`）：
   - 脂肪酸缩写：`MUFA`→单不饱和脂肪酸、`PUFA`→多不饱和脂肪酸、`SFA`→饱和脂肪酸；
   - 脂肪酸记号 `C:D`（碳链:双键）：保留记号，如 `12:1` → `12:1 脂肪酸` 或对应具体酸名（如 `12:0` → 月桂酸）；
   - 维生素学名：`Vitamin E (alpha-tocopherol)` → `维生素E（α-生育酚）`；
   - 与 172 表已有条目语义一致的，**沿用 172 表的中文用词**（避免同物异名）——Agent 应先 db_read 抽样 `SELECT DISTINCT name, name_zh FROM usda_food_nutrients WHERE name_zh IS NOT NULL` 对照已有译法。
3. **守卫 UPDATE**：
   ```sql
   UPDATE usda_food_nutrients
   SET name_zh='<译文>'
   WHERE name='<原名>' AND name_zh IS NULL;
   ```
   `AND name_zh IS NULL` 防止覆盖已被 172 表或现有 API 译过的行。一条 UPDATE 覆盖同名的所有行（nutrient name 跨 fdc_id 重复）。
4. **复核**：UPDATE 后 `db_read` 再查 `unmapped` 计数下降、抽查译文。

### 守卫清单

- 只 UPDATE `usda_food_nutrients.name_zh`，不动其它字段/表。
- 每条 UPDATE 带 `WHERE name=... AND name_zh IS NULL`。
- 不改 172 静态表源码（`nutrient_mapping.py`）。
- 译文与 172 表已有用词保持一致（先对照再译）。

### 待核对

- [ ] **方案 A vs 「不做」取舍**（同 Task 2-2 的 gate）。
- [ ] USDA 数据未入库时无数据可处理——验收前确认 `GET /api/v1/admin/usda/statistics` 的 `nutrients > 0` 且 `unmapped_nutrients > 0`。
- [ ] 172 表是否需要因 Agent 新译成果而扩展——阶段 2 不做（改源码超范围），仅记入「待办」。

---

## 实施步骤（每个任务通用）

1. **`task_templates.py` 加模板**：在 `TASK_TEMPLATES` 字典追加条目，删顶部阶段 2 占位注释。每个模板含 `title`（前端按钮文案）/ `prompt`（上述各 Task 的完整 prompt）/ `allowed_tools`（复用 `_READ_ONLY_TOOLS`）。
2. **落点表/字段确认**：
   - `fill_density`：`entity_densities` 已存在，**无需迁移、无需 SQL 脚本**。
   - `usda_translate` / `unmapped_nutrient_translate`：`usda_foods` / `usda_food_nutrients` 已存在，**无需迁移**。
3. **prompt 渲染测试**：写 pytest 单测（参考阶段 1 对 `fill_piece_weight` 的测试风格），断言 `get_template('fill_density')['prompt']` 非空、含关键守卫词（如 `entity_densities`、`kg/m³`、`source='agent'`）。
4. **小范围真跑**：起一个 `fill_density` 会话，让 Agent 先摸底（只 db_read），人工 review 其摸底结论合理后再放行 INSERT；INSERT 后抽查 `entity_densities` 行数与抽样密度值。
5. **端到端验收**：
   - 任务台前端出现新按钮；
   - 点击 → 流式对话正常 → sql_guard 判级正确（safe INSERT 自动执行 / 若判 dangerous 则走审批）；
   - 会话刷新可回看；
   - 目标表数据按预期增长，`source='agent'` 标记正确。

---

## 风险与待核对（汇总，执行前逐条过）

### 密度单位坑（Task 2-1，最高优先）
- [ ] **`entity_densities` 用 kg/m³，`Ingredient.density` 用 g/mL**——数值差 1000 倍。prompt 必须写死 kg/m³，常识参考表也用 kg/m³。已确认（`entity_density.py:13` 注释 + `unit_conversion_service.get_density()` 注释 + `WATER_DENSITY` 常量）。
- [ ] sql_guard 对 `INSERT ... SELECT ... WHERE NOT EXISTS` 的判级——阶段 1 只验过 UPDATE/DELETE，需测试确认。

### USDA 翻译「是否真需要 Agent」（Task 2-2 / 2-3，gate）
- [ ] **两个翻译任务都已有完整后端服务 + API**（`TranslateTask` / `TranslateNutrientsTask` + `POST /usda/translate` / `POST /usda/translate-nutrients`）。Agent 的增量价值有限，**执行前开发者需明确取舍**：
  - 方案 A：不建 Agent 任务，保持现有 API；
  - 方案 B：建 Agent 任务作为兜底/复核通道（Task 2-3 因营养素需要专家知识，价值高于 Task 2-2）。
- [ ] **USDA 数据当前未入库**（`usda_foods` / `usda_food_nutrients` 均 0 行）——后两个任务无论是否建模板，端到端验收前都必须先跑 USDA 下载导入（`POST /api/v1/admin/usda/download`）。

### 营养素映射表扩展（Task 2-3）
- [ ] Agent 新译的营养素名是否应回填到 172 静态表（`nutrient_mapping.py`）——会改 Python 源码，**阶段 2 不做**，记入后续待办。当前只写 `usda_food_nutrients.name_zh`，不影响现有匹配（`matcher.py` 走 `name_zh` 或归一化 key）。

### 通用
- [ ] Agent 单轮 SQL 块数量上限（影响批量任务的单轮吞吐）——建议 ≤ 50 条/轮，多轮推进。
- [ ] 三个任务的 `title` 文案（前端按钮）——建议：
  - `fill_density` → 「补食材密度（体积↔质量换算）」
  - `usda_translate` → 「USDA 食材名翻译（兜底）」
  - `unmapped_nutrient_translate` → 「未映射营养素名翻译」

---

## 探索依据索引（执行者复核用）

- 密度模型：`backend/app/models/entity_density.py`（kg/m³）、`backend/app/models/ingredient_density.py`（DEPRECATED）、`backend/app/models/nutrition.py:25`（`Ingredient.density` g/mL 注释）
- 密度消费者：`backend/app/services/unit_conversion_service.py:72-132`（`get_density` 优先级链）
- 密度 AI 推测（旧字段，单位坑来源）：`backend/app/services/importer/ai_inference/inferrer.py:185-231`（`infer_densities` 写 `Ingredient.density` 用 g/cm³）
- 172 营养素映射表：`backend/app/services/usda/nutrient_mapping.py:18`（`NUTRIENT_TRANSLATIONS`，实测 172 条）、`map_nutrient_name()`
- 食材翻译服务：`backend/app/services/translate/task.py`（`TranslateTask`）、`backend/app/services/translate/base.py:5`（`FOOD_TRANSLATION_SYSTEM_PROMPT`）
- 营养素翻译服务：`backend/app/services/translate/nutrient_task.py`（`TranslateNutrientsTask`）、`backend/app/services/translate/base.py:13`（`NUTRIENT_TRANSLATION_SYSTEM_PROMPT`）
- USDA Admin API：`backend/app/api/usda_admin.py:254`（`/usda/translate`）、`:285`（`/usda/translate-nutrients`）、`:112`（`/usda/unmapped-nutrients`）、`:102`（statistics 含 `unmapped_nutrients`）
- USDA 模型：`backend/app/models/usda.py`（`UsdaFood.description_zh`/`translate_status`、`UsdaFoodNutrient.name`/`name_zh`、`TranslationConfig`、`UsdaTask`）
- 阶段 1 模板（参考风格）：`backend/app/services/agent/task_templates.py:29-110`（`_FILL_PIECE_WEIGHT_PROMPT`）
