# Agent 维护任务扩展：密度推测 / USDA 翻译 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将「推测密度」「USDA 食材名翻译」「未映射营养素翻译」三个功能的操作入口迁移到统一「数据维护中心」页面，并为其添加 Agent（Claude Code CLI）批量处理支持。

**Architecture:** 后端在 `task_templates.py` 新增三个 Agent 任务模板（`infer_densities` / `usda_translate` / `unmapped_nutrient_translate`），复用已有 `ClaudeCodeRunner` + 受控 MCP + `sql_guard` 管线；旧 `inferrer.py` 修复写入目标为 `EntityDensity` 表。前端新建 `DataMaintenanceView.vue` 统一页面，整合菜谱导入 + USDA 操作 + 统一任务列表，复用 `infer_quantities` 确立的双路径（Agent for claude_code / 旧 API for 其他 provider）和会话跟踪模式。

**Tech Stack:** Python/FastAPI + Vue 3/TypeScript + Claude Code CLI (Agent)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/services/agent/task_templates.py` | 修改 | 新增 3 个 prompt 常量 + 3 条 TASK_TEMPLATES 条目 |
| `backend/app/services/importer/ai_inference/inferrer.py` | 修改 | `infer_densities` 写入目标改为 `EntityDensity` + 自动 *1000 单位转换 |
| `frontend/src/views/admin/DataMaintenanceView.vue` | **新建** | 统一数据维护中心页面（基于 RecipeImportView 改造） |
| `frontend/src/router/index.ts` | 修改 | 新增 `/admin/data-maintenance` 路由；`/admin/recipe-import` 重定向 |
| `frontend/src/views/admin/AdminDashboard.vue` | 修改 | 「菜谱导入」卡片改为「数据维护中心」，链接更新 |
| `frontend/src/views/admin/UsdaDataView.vue` | 修改 | 移除翻译操作按钮和 provider 选择器，保留统计数据查看 |

---

### Task 1: 后端 — 新增三个 Agent 任务模板

**Files:**
- Modify: `backend/app/services/agent/task_templates.py`

**参考：** 已有的 `_INFER_QUANTITIES_PROMPT`（第 117-288 行）和 `_FILL_PIECE_WEIGHT_PROMPT`（第 29-114 行）的 prompt 结构。

- [ ] **Step 1: 在 TASK_TEMPLATES 前新增 `_INFER_DENSITIES_PROMPT` 常量**

在 `_INFER_QUANTITIES_PROMPT` 之后（第 288 行之后）、`TASK_TEMPLATES` 定义之前插入：

```python
_INFER_DENSITIES_PROMPT = """你是「生计」应用的食材密度维护助手，专门负责推断食材的密度（kg/m³）——用于体积↔质量换算（如「毫升→克」「杯→克」）。

# 任务目标
为 ``entity_densities`` 表补充缺失的食材密度值（entity_type='ingredient'）。
当前 ``ingredients`` 表中有大量原料 ``density`` 字段为 NULL（旧字段，已废弃），
``entity_densities`` 表可能为空，需要从常识推断密度后 INSERT 缺失记录。

**重要：密度单位是 kg/m³，不是 g/cm³。** 水的密度是 1000 kg/m³（不是 1.0）。

# 数据库访问
你通过以下方式访问数据库（取决于环境配置，至少有一种可用）：

**1. 只读查询（两种方式，环境自动选择一种）：**
   - **MCP 工具**（优先）：``mcp__controlled_db__db_read``——执行 SELECT 查询；
     ``mcp__controlled_db__describe``——查看表结构；
     ``mcp__controlled_db__list_tables``——列出所有表。
   - **bash 命令**（备选）：如果上述 MCP 工具不可用，用 bash 调用
     ``python -m app.services.agent.db_query "SELECT..."`` 执行查询。

**2. 写操作（统一方式）：**
   **在你的回复正文里用 ```sql``` 代码块输出 SQL**——系统的 sql_extractor 会自动
   提取，sql_guard 判定：
   - 安全 SQL（INSERT / 带 WHERE 的 UPDATE）自动执行；
   - 危险 SQL（DELETE / 无 WHERE 的 UPDATE / DROP 等）会生成审批记录交给管理员审批。

不要调用不存在的工具，也不要把 SQL 写在普通段落里（必须用 ```sql``` 围栏）。

# 工作流程
按以下步骤推进，每一步先观察再决策：

## 第一步：摸底统计

用 db_read 执行以下查询，了解需要处理的缺失规模：

1. **查看 entity_densities 已有数据量**：
   ```sql
   SELECT entity_type, COUNT(*) AS cnt FROM entity_densities GROUP BY entity_type;
   ```

2. **查看 ingredients 中哪些缺少密度记录**：
   ```sql
   SELECT COUNT(*) AS total, SUM(CASE WHEN ed.id IS NULL THEN 1 ELSE 0 END) AS missing
   FROM ingredients i
   LEFT JOIN entity_densities ed ON ed.entity_type = 'ingredient' AND ed.entity_id = i.id AND ed.condition IS NULL
   WHERE i.is_active = 1;
   ```

3. **拉取具体缺失清单**（用于估值）：
   ```sql
   SELECT i.id, i.name, i.category_id
   FROM ingredients i
   LEFT JOIN entity_densities ed ON ed.entity_type = 'ingredient' AND ed.entity_id = i.id AND ed.condition IS NULL
   WHERE i.is_active = 1 AND ed.id IS NULL
   ORDER BY i.category_id, i.name;
   ```

## 第二步：分类估值

对每条缺失密度的食材，按以下分类结合常识推断密度值（**单位：kg/m³**）：

### 常见食材密度参考（kg/m³）
| 类别 | 食材 | 密度 (kg/m³) |
|------|------|-------------|
| 液体 | 水 | 1000 |
| 液体 | 食用油 | 920 |
| 液体 | 蜂蜜 | 1420 |
| 液体 | 牛奶 | 1030 |
| 液体 | 酱油 | 1150 |
| 液体 | 醋 | 1010 |
| 粉状 | 面粉（松散） | 550 |
| 粉状 | 白砂糖 | 850 |
| 粉状 | 盐 | 1200 |
| 粉状 | 淀粉 | 600 |
| 粉状 | 可可粉 | 400 |
| 粉状 | 泡打粉 | 700 |
| 颗粒 | 大米 | 850 |
| 颗粒 | 小米 | 800 |
| 颗粒 | 燕麦 | 400 |
| 颗粒 | 坚果（整粒） | 650 |
| 固体 | 黄油 | 910 |
| 固体 | 芝士（碎） | 500 |
| 固体 | 面包糠 | 200 |

### 估值原则
- 液体类（油/水/酱/醋/蜂蜜/牛奶）：按液体密度常识，绝大多数在 900-1400 区间
- 粉状（面粉/糖/盐/淀粉/可可粉）：按松散堆密度（packed 密度更高，取 loose 值）
- 整粒固体（米/豆/坚果）：按颗粒堆密度
- **气体/叶片状调味料（八角、香叶等）密度无意义**，跳过不强行造数
- 复合调味料（如「麻辣香锅料」）：按典型调味酱密度 ~1100 估算
- 不熟悉的食材：搜索同类食材，给出合理估值并标注依据

## 第三步：INSERT 缺失记录

按以下规则输出 INSERT SQL：

```sql
INSERT INTO entity_densities (entity_type, entity_id, density, temperature, condition, source, confidence, created_at, updated_at)
SELECT 'ingredient', :ingredient_id, :density_value, 20.0, NULL, 'agent', :confidence_level, datetime('now'), datetime('now')
WHERE NOT EXISTS (
  SELECT 1 FROM entity_densities
  WHERE entity_type = 'ingredient' AND entity_id = :ingredient_id AND condition IS NULL
);
```

**核心规则：**
- 每条 INSERT 单独一个 ```sql``` 围栏块
- 必须带 `WHERE NOT EXISTS` 防重守卫
- `source='agent'` 标记本次维护来源
- `confidence`：液体/常见粉状给 0.9，冷门食材给 0.7
- `temperature`：常温给 20.0，无温度依赖可 NULL
- `condition`：默认不填（NULL = 常温常态）
- 按合理值分组批量 INSERT，不要逐条单独 INSERT
- **不要涉及 `ingredients.density` 字段**（旧字段，已废弃）

## 第四步：复核

执行后重新查询确认：
```sql
SELECT COUNT(*) AS remaining
FROM ingredients i
LEFT JOIN entity_densities ed ON ed.entity_type = 'ingredient' AND ed.entity_id = i.id AND ed.condition IS NULL
WHERE i.is_active = 1 AND ed.id IS NULL;
```

确认剩余条数为 0 或合理可忽略的少数（无法估值的叶片香料等）。

# 输出格式约束
- 每条写操作 SQL 单独一个 ```sql``` 围栏块。
- SELECT 查询也用 ```sql``` 块包裹（但通过实际查询工具执行，不会被作为写操作处理）。
- 修正前后给出简短结论：本轮处理了 N 条、覆盖哪些类别。

# 重要
- **全部自己决策，不问用户。** 即使是不常见的食材，也要基于常识/典型规格给出合理的估计值直接 INSERT——不要把条目列成清单问用户。
- 水的密度是 **1000 kg/m³**，不是 1.0。输出时注意单位。
- 如果某食材已有密度记录（entity_densities 中已存在），不要重复 INSERT。
"""
```

- [ ] **Step 2: 新增 `_USDA_TRANSLATE_PROMPT` 常量**

在 `_INFER_DENSITIES_PROMPT` 之后插入：

```python
_USDA_TRANSLATE_PROMPT = """你是「生计」应用的 USDA 食材名翻译助手，专门负责将 USDA 数据库中英文食材名翻译为中文。

# 任务目标
翻译 ``usda_foods`` 表中 ``translate_status`` 为 'pending' 的英文食材描述（``description`` 字段），
将译文写入 ``description_zh`` 字段，并标记 ``translate_status = 'done'``。

# 数据库访问
你通过以下方式访问数据库（取决于环境配置，至少有一种可用）：

**1. 只读查询（两种方式，环境自动选择一种）：**
   - **MCP 工具**（优先）：``mcp__controlled_db__db_read``——执行 SELECT 查询；
     ``mcp__controlled_db__describe``——查看表结构；
     ``mcp__controlled_db__list_tables``——列出所有表。
   - **bash 命令**（备选）：如果上述 MCP 工具不可用，用 bash 调用
     ``python -m app.services.agent.db_query "SELECT..."`` 执行查询。

**2. 写操作（统一方式）：**
   **在你的回复正文里用 ```sql``` 代码块输出 SQL**——系统的 sql_extractor 会自动
   提取，sql_guard 判定：
   - 安全 SQL（INSERT / 带 WHERE 的 UPDATE）自动执行；
   - 危险 SQL（DELETE / 无 WHERE 的 UPDATE / DROP 等）会生成审批记录交给管理员审批。

不要调用不存在的工具，也不要把 SQL 写在普通段落里（必须用 ```sql``` 围栏）。

# 工作流程

## 第一步：摸底

```sql
SELECT translate_status, COUNT(*) AS cnt
FROM usda_foods
GROUP BY translate_status;
```

如果 total = 0，直接报告「USDA 数据未就绪，请先下载 USDA 数据」并结束任务。

## 第二步：拉取待翻译条目

```sql
SELECT fdc_id, description
FROM usda_foods
WHERE translate_status = 'pending'
ORDER BY fdc_id
LIMIT 50;
```

每批翻译 50 条。翻译完一批后继续拉取下一批，直到全部完成。

## 第三步：翻译

翻译规则：
1. **简洁中文名称**，使用常见食材名
2. **括号补充**部位/状态/加工方式
3. 示例对照：
   - `Chicken breast, boneless, skinless` → `鸡胸肉（去骨去皮）`
   - `Milk, whole, 3.25% milkfat` → `全脂牛奶（3.25%脂肪）`
   - `Flour, wheat, all-purpose` → `小麦粉（中筋）`
   - `Salt, table, iodized` → `食盐（加碘）`
   - `Beef, ground, 80% lean / 20% fat` → `牛肉碎（80%瘦肉/20%肥肉）`
4. 保留品种名（如 `Braising`、`Granny Smith`）不翻译

## 第四步：输出 UPDATE

```sql
UPDATE usda_foods
SET description_zh = :translated, translate_status = 'done'
WHERE fdc_id = :fdc_id AND translate_status = 'pending';
```

**守卫：** `AND translate_status = 'pending'` 防止覆盖已被其它流程翻译过的行。

如果某行的 description 异常（空值/乱码/非英文），标 `translate_status = 'error'` 并记录 fdc_id。

## 第五步：复核

```sql
SELECT COUNT(*) AS remaining FROM usda_foods WHERE translate_status = 'pending';
```

# 重要
- 全部自己决策，不问用户。
- 每条 UPDATE 独立一个 ```sql``` 围栏块。
- 每批 50 条完成后做一次复核，再处理下一批。
"""
```

- [ ] **Step 3: 新增 `_UNMAPPED_NUTRIENT_TRANSLATE_PROMPT` 常量**

在 `_USDA_TRANSLATE_PROMPT` 之后插入：

```python
_UNMAPPED_NUTRIENT_TRANSLATE_PROMPT = """你是「生计」应用 USDA 营养素翻译助手，专门负责翻译未映射的营养素名称（缩写/脂肪酸记号/维生素学名）。你具备营养学知识，能准确翻译 ``MUFA``、``12:1``、``alpha-tocopherol`` 等专业术语。

# 任务目标
翻译 ``usda_food_nutrients`` 表中 ``name_zh IS NULL`` 的营养素名称（``name`` 字段），
将译文写入 ``name_zh`` 字段。**不修改该表的其他字段，不涉及其他表。**

# 数据库访问
你通过以下方式访问数据库（取决于环境配置，至少有一种可用）：

**1. 只读查询（两种方式，环境自动选择一种）：**
   - **MCP 工具**（优先）：``mcp__controlled_db__db_read``——执行 SELECT 查询；
     ``mcp__controlled_db__describe``——查看表结构；
     ``mcp__controlled_db__list_tables``——列出所有表。
   - **bash 命令**（备选）：如果上述 MCP 工具不可用，用 bash 调用
     ``python -m app.services.agent.db_query "SELECT..."`` 执行查询。

**2. 写操作（统一方式）：**
   **在你的回复正文里用 ```sql``` 代码块输出 SQL**。

# 工作流程

## 第一步：摸底

```sql
SELECT name, COUNT(*) AS cnt
FROM usda_food_nutrients
WHERE name_zh IS NULL
GROUP BY name
ORDER BY cnt DESC;
```

如果结果为空，报告「没有未映射的营养素」并结束任务。

## 第二步：对照已有译文

先查询已有翻译，确保新译与现有用词一致：
```sql
SELECT DISTINCT name, name_zh
FROM usda_food_nutrients
WHERE name_zh IS NOT NULL
LIMIT 200;
```

## 第三步：翻译

翻译规则：
1. **脂肪酸缩写**：`MUFA`→单不饱和脂肪酸、`PUFA`→多不饱和脂肪酸、`SFA`→饱和脂肪酸
2. **脂肪酸记号 `C:D`**（碳链数:双键数）：
   - `12:0`→月桂酸（沿用 172 表用词）
   - `14:0`→肉豆蔻酸
   - `16:0`→棕榈酸
   - `18:0`→硬脂酸
   - `18:1`→油酸
   - `18:2`→亚油酸
   - `18:3`→亚麻酸
   - 其他如 `12:1`→12:1 脂肪酸（保留记号，加「脂肪酸」后缀）
3. **维生素/矿物质学名**：
   - `Vitamin E (alpha-tocopherol)`→维生素E（α-生育酚）
   - `Vitamin K (phylloquinone)`→维生素K（叶绿醌）
   - `Folate, total`→叶酸（总量）
4. **与已有译文一致**：如果已有译文中有相同营养素的翻译，沿用其用词

## 第四步：输出 UPDATE

```sql
UPDATE usda_food_nutrients
SET name_zh = :translated
WHERE name = :original_name AND name_zh IS NULL;
```

**守卫：** `AND name_zh IS NULL` 防止覆盖已被 172 表或现有 API 译过的行。
一条 UPDATE 会覆盖同名所有行（nutrient name 跨 fdc_id 重复）。**不需要 WHERE id IN (...)**。
单轮处理最多 50 条 distinct name。

## 第五步：复核

```sql
SELECT COUNT(*) AS remaining
FROM usda_food_nutrients
WHERE name_zh IS NULL;
```

# 重要
- 全部自己决策，不问用户。
- 每条 UPDATE 独立一个 ```sql``` 围栏块。
- 译文与已有 172 表用词保持一致（先对照拉取结果再译）。
- 不确定的特殊记号，保留原名并在说明里标注。
"""
```

- [ ] **Step 4: 在 `TASK_TEMPLATES` 注册三条新模板**

将第 291-307 行的 `TASK_TEMPLATES` 字典替换为：

```python
TASK_TEMPLATES: dict[str, dict] = {
    "fill_piece_weight": {
        "title": "补单位质量（自定义单位对应克数）",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _FILL_PIECE_WEIGHT_PROMPT,
    },
    "infer_quantities": {
        "title": "推测模糊量（菜谱原料用量推理）",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _INFER_QUANTITIES_PROMPT,
    },
    "infer_densities": {
        "title": "推测密度（体积↔质量换算）",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _INFER_DENSITIES_PROMPT,
    },
    "usda_translate": {
        "title": "USDA 食材名翻译",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _USDA_TRANSLATE_PROMPT,
    },
    "unmapped_nutrient_translate": {
        "title": "未映射营养素名翻译",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _UNMAPPED_NUTRIENT_TRANSLATE_PROMPT,
    },
}
```

同时删除第 302-306 行的阶段 2 占位注释。

- [ ] **Step 5: 验证模板注册**

在 `backend/` 目录下运行：

```bash
uv run python -c "from app.services.agent.task_templates import list_task_types; print(list_task_types())"
```

预期输出应包含 5 个任务类型（fill_piece_weight / infer_quantities / infer_densities / usda_translate / unmapped_nutrient_translate）。

---

### Task 2: 后端 — 修复 inferrer.py 密度写入目标

**Files:**
- Modify: `backend/app/services/importer/ai_inference/inferrer.py`

- [ ] **Step 1: 添加 EntityDensity 导入**

在文件顶部的 import 块中添加：

```python
from app.models.entity_density import EntityDensity
```

- [ ] **Step 2: 重写 `infer_densities` 方法**

将第 185-231 行的 `infer_densities` 方法替换为：

```python
def infer_densities(self, force: bool = False,
                     progress_callback: Optional[Callable] = None) -> ImportResult:
    """推测没有密度值的原料的密度，写入 entity_densities 表（kg/m³）。"""
    result = ImportResult()

    # 找出缺少 density 的原料（与 entity_densities 左连接）
    from sqlalchemy import not_
    existing_ids = (
        self.db.query(EntityDensity.entity_id)
        .filter(EntityDensity.entity_type == 'ingredient', EntityDensity.condition.is_(None))
        .subquery()
    )
    query = self.db.query(Ingredient).filter(
        Ingredient.is_active == True,
        not_(Ingredient.id.in_(existing_ids)),
    )

    candidates = query.all()
    if not candidates:
        result.warnings.append("没有需要推测密度的原料（entity_densities 均已覆盖）")
        return result

    total = len(candidates)
    inferred = 0
    for idx, ingredient in enumerate(candidates, 1):
        if progress_callback:
            progress_callback("密度推测", idx, total,
                              f"{ingredient.name} ({idx}/{total})")
        prompt = (
            f"请推测食材\"{ingredient.name}\"的密度（g/cm³），"
            f"即每毫升多少克。\n"
            f"常见参考：水=1.0，食用油≈0.92，蜂蜜≈1.4，面粉≈0.55。\n"
            f"返回 JSON：{{\"density_g_per_cm3\": 数值}}"
        )

        try:
            response_text = self.ai_caller(prompt) if self.ai_caller else None
            if not response_text:
                continue

            parsed = json.loads(response_text)
            density = parsed.get("density_g_per_cm3")
            if density is not None:
                # AI 返回 g/cm³，entity_densities 需 kg/m³（×1000）
                ed = EntityDensity(
                    entity_type='ingredient',
                    entity_id=ingredient.id,
                    density=round(density * 1000, 6),
                    temperature=20.0,
                    source='ai_inferrer',
                    confidence=0.8,
                )
                self.db.add(ed)
                inferred += 1

        except (json.JSONDecodeError, Exception) as e:
            result.errors.append(
                f"密度推测失败 {ingredient.name}(id={ingredient.id}): {str(e)}"
            )

    self.db.commit()
    result.stats["densities"] = inferred
    return result
```

**核心变更：**
1. 从 `self.db.query(Ingredient).filter(Ingredient.density.is_(None))` 改为 LEFT JOIN `entity_densities` 查缺失（避免重复 INSERT）
2. 写入目标从 `ingredient.density = density` 改为 `EntityDensity(...)` 模型
3. 自动 `density * 1000`（g/cm³ → kg/m³）
4. 标记 `source='ai_inferrer'` 区分于 Agent 的 `source='agent'`

- [ ] **Step 3: 验证后端无语法错误**

```bash
cd backend && uv run python -c "from app.services.importer.ai_inference.inferrer import AIInferrer; print('OK')"
```

---

### Task 3: 前端 — 新建 DataMaintenanceView.vue

**Files:**
- Create: `frontend/src/views/admin/DataMaintenanceView.vue`

此任务工作量较大，分多个子步骤。

- [ ] **Step 1: 复制 RecipeImportView.vue 为基础**

将 `frontend/src/views/admin/RecipeImportView.vue` 复制为 `frontend/src/views/admin/DataMaintenanceView.vue`。

- [ ] **Step 2: 修改标题和布局**

将 app-bar title 从 `菜谱导入管理` 改为 `数据维护中心`。

在「上传压缩包导入」卡片之后、「AI 推测处理」卡片之前，插入 USDA 数据管理卡片：

```vue
      <!-- USDA 数据管理 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="deep-orange">mdi-database</v-icon>
            <span>USDA 数据管理</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              管理 USDA 营养数据库的原始数据下载与统计查看。
            </p>

            <!-- 统计摘要 -->
            <div v-if="usdaStats.total" class="text-caption mb-3">
              <v-chip size="small" variant="tonal" class="mr-1 mb-1">
                总食材 {{ usdaStats.total }}
              </v-chip>
              <v-chip size="small" variant="tonal" class="mr-1 mb-1">
                总营养素 {{ usdaStats.nutrients }}
              </v-chip>
              <v-chip size="small" variant="tonal" class="mr-1 mb-1">
                已映射 {{ usdaStats.mapped_pct || 0 }}%
              </v-chip>
            </div>

            <v-row class="mt-1">
              <v-col cols="6">
                <v-btn
                  block color="deep-orange" variant="tonal"
                  :loading="usdaDownloading"
                  @click="downloadUsdaData"
                >
                  <v-icon start>mdi-download</v-icon>
                  下载 USDA
                </v-btn>
              </v-col>
              <v-col cols="6">
                <v-btn
                  block color="deep-orange" variant="tonal"
                  :loading="usdaUploading"
                  @click="triggerUsdaUpload"
                >
                  <v-icon start>mdi-upload</v-icon>
                  上传 ZIP
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
```

- [ ] **Step 3: 改造 AI 维护区域 — 添加两个选择器和四个按钮**

将原有的「AI 推测处理」卡片（第 143-201 行）替换为：

```vue
      <!-- AI 维护 -->
      <v-col cols="12" md="6" lg="4">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2" color="purple">mdi-robot</v-icon>
            <span>AI 维护</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-6">
            <p class="text-body-2 mb-4">
              使用 AI 推断食材用量和密度，翻译 USDA 食材名和营养素名。
            </p>

            <!-- AI 推断后端选择 -->
            <v-select
              v-model="aiInferProvider"
              :items="enabledAiProviders"
              label="AI 推断后端"
              variant="outlined"
              prepend-icon="mdi-brain"
              hint="用于模糊量、密度、营养素翻译"
              persistent-hint
              hide-details
              class="mb-3"
            />

            <!-- 翻译后端选择 -->
            <v-select
              v-model="translateProvider"
              :items="enabledTranslateProviders"
              label="翻译后端"
              variant="outlined"
              prepend-icon="mdi-translate"
              hint="用于食材名翻译（AI + 机翻）"
              persistent-hint
              hide-details
              class="mb-3"
            />

            <v-checkbox v-model="aiForce" label="强制重新处理全部" hide-details class="mb-3" />

            <v-row>
              <v-col cols="6">
                <v-btn
                  block color="purple" variant="tonal"
                  :loading="submitting.aiQuantities"
                  :disabled="!enabledAiProviders.length"
                  @click="inferQuantities"
                >
                  <v-icon start>mdi-scale</v-icon>
                  推测模糊量
                </v-btn>
              </v-col>
              <v-col cols="6">
                <v-btn
                  block color="purple" variant="tonal"
                  :loading="submitting.aiDensities"
                  :disabled="!enabledAiProviders.length"
                  @click="inferDensities"
                >
                  <v-icon start>mdi-database</v-icon>
                  推测密度
                </v-btn>
              </v-col>
              <v-col cols="6" class="mt-2">
                <v-btn
                  block color="purple" variant="tonal"
                  :loading="submitting.translateFoods"
                  :disabled="!enabledTranslateProviders.length"
                  @click="onTranslateFoods"
                >
                  <v-icon start>mdi-food-apple</v-icon>
                  食材名翻译
                </v-btn>
              </v-col>
              <v-col cols="6" class="mt-2">
                <v-btn
                  block color="purple" variant="tonal"
                  :loading="submitting.translateNutrients"
                  :disabled="!enabledAiProviders.length"
                  @click="onTranslateNutrients"
                >
                  <v-icon start>mdi-flask</v-icon>
                  营养素翻译
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
```

- [ ] **Step 4: 添加 USDA 未映射营养素列表（可折叠）**

在任务列表之前插入可折叠的未映射营养素区块：

```vue
      <!-- 未映射营养素（可折叠） -->
      <v-col cols="12">
        <v-card class="rounded-lg">
          <v-card-title class="d-flex align-center py-4" style="cursor: pointer" @click="showUnmapped = !showUnmapped">
            <v-icon class="mr-2">mdi-flask-outline</v-icon>
            <span>未映射营养素（{{ unmappedNutrients.length }} 个）</span>
            <v-spacer />
            <v-icon>{{ showUnmapped ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
          </v-card-title>
          <v-divider />
          <v-card-text v-if="showUnmapped" class="pt-4">
            <v-chip
              v-for="n in unmappedNutrients" :key="n"
              class="ma-1" size="small" variant="tonal"
            >
              {{ n }}
            </v-chip>
            <p v-if="!unmappedNutrients.length" class="text-caption text-medium-emphasis">
              暂无未映射营养素（请先下载 USDA 数据）
            </p>
          </v-card-text>
        </v-card>
      </v-col>
```

- [ ] **Step 5: 更新 `<script setup>` — 导入和状态**

将原有的 `<script setup>` 扩展为包含 USDA 相关导入和状态：

```typescript
<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useImportTask } from '@/composables/useImportTask'
import { getTranslationConfig, getUsdaStatistics, getUnmappedNutrients, downloadUsda, uploadUsda, translateUsda, translateNutrients } from '@/api/usda'
import { createSession, getSession, listSessions } from '@/api/agent'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { tasks, fetchTasks, startTask, startUploadTask } = useImportTask()
const router = useRouter()

const goBack = () => router.back()

// 各卡片提交中状态
const submitting = reactive({
  repo: false, local: false, upload: false,
  aiQuantities: false, aiDensities: false,
  translateFoods: false, translateNutrients: false,
})

const errorMessage = ref('')
const localPath = ref('')
const uploadFile = ref<File | null>(null)
const aiForce = ref(false)
```

- [ ] **Step 6: 添加 USAD 数据显示和操作函数**

在 `<script setup>` 中添加：

```typescript
// === USDA 数据管理 ===
const usdaStats = ref<any>({})
const unmappedNutrients = ref<string[]>([])
const showUnmapped = ref(false)
const usdaDownloading = ref(false)
const usdaUploading = ref(false)
const usdaFileInput = ref<HTMLInputElement | null>(null)

async function loadUsdaStats() {
  try {
    const s = await getUsdaStatistics()
    usdaStats.value = s
  } catch { /* 忽略 */ }
}

async function loadUnmapped() {
  try {
    unmappedNutrients.value = await getUnmappedNutrients()
  } catch { /* 忽略 */ }
}

async function downloadUsdaData() {
  usdaDownloading.value = true
  try {
    await downloadUsda()
    errorMessage.value = 'USDA 数据下载任务已启动'
  } catch (e: any) {
    errorMessage.value = e?.userMessage || 'USDA 数据下载失败'
  }
  usdaDownloading.value = false
}

function triggerUsdaUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.zip'
  input.onchange = async (e: any) => {
    const file = e.target?.files?.[0]
    if (!file) return
    usdaUploading.value = true
    try {
      await uploadUsda(file)
      errorMessage.value = 'USDA 数据上传成功'
    } catch (e: any) {
      errorMessage.value = e?.userMessage || 'USDA 数据上传失败'
    }
    usdaUploading.value = false
  }
  input.click()
}
```

- [ ] **Step 7: 添加两个选择器的 computed 属性**

```typescript
// === AI 提供方选择 ===
const translationConfig = ref<any>(null)
const aiInferProvider = ref('')
const translateProvider = ref('')

function enabledIn(region: string): string[] {
  const cfg = translationConfig.value
  if (!cfg) return []
  const provs = cfg[region]?.providers || {}
  return Object.entries(provs)
    .filter(([, v]: any) => v.enabled !== false)
    .map(([k]) => k)
}

// AI 推断后端：仅 AI 类（用于模糊量、密度、营养素翻译）
const enabledAiProviders = computed<string[]>(() => enabledIn('ai'))

// 翻译后端：AI + 机翻（用于食材名翻译）
const enabledTranslateProviders = computed<string[]>(() => [
  ...enabledIn('ai'),
  ...enabledIn('machine'),
])
```

- [ ] **Step 8: 添加四个按钮的操作函数**

```typescript
// === 四合一按钮逻辑 ===

async function inferQuantities() {
  submitting.aiQuantities = true
  try {
    const provider = aiInferProvider.value || 'claude_code'
    if (provider === 'claude_code') {
      const { session_id } = await createSession('infer_quantities', aiForce.value)
      agentTasks.value.unshift({
        session_id, task_type: 'infer_quantities',
        label: 'Agent 模糊量推测', status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      const taskId = await startTask('/import/ai-infer/quantities', {
        params: { force: aiForce.value, provider },
      })
      if (!taskId) errorMessage.value = '模糊量推测任务启动失败'
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '模糊量推测任务启动失败'
  }
  submitting.aiQuantities = false
}

async function inferDensities() {
  submitting.aiDensities = true
  try {
    const provider = aiInferProvider.value || 'claude_code'
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
      if (!taskId) errorMessage.value = '密度推测任务启动失败'
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '密度推测任务启动失败'
  }
  submitting.aiDensities = false
}

async function onTranslateFoods() {
  submitting.translateFoods = true
  try {
    const provider = translateProvider.value || 'claude_code'
    if (provider === 'claude_code') {
      const { session_id } = await createSession('usda_translate')
      agentTasks.value.unshift({
        session_id, task_type: 'usda_translate',
        label: 'Agent 食材名翻译', status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      await translateUsda(provider)
      errorMessage.value = '食材名翻译任务已启动'
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '食材名翻译任务启动失败'
  }
  submitting.translateFoods = false
}

async function onTranslateNutrients() {
  submitting.translateNutrients = true
  try {
    const provider = aiInferProvider.value || 'claude_code'
    if (!unmappedNutrients.value.length && provider !== 'claude_code') {
      errorMessage.value = '没有未映射的营养素'
      return
    }
    if (provider === 'claude_code') {
      const { session_id } = await createSession('unmapped_nutrient_translate')
      agentTasks.value.unshift({
        session_id, task_type: 'unmapped_nutrient_translate',
        label: 'Agent 营养素翻译', status: 'pending',
        created_at: new Date().toISOString(),
      })
      startAgentPolling(session_id)
    } else {
      await translateNutrients(provider)
      errorMessage.value = '营养素翻译任务已启动'
    }
  } catch (e: any) {
    errorMessage.value = e?.response?.data?.detail || '营养素翻译任务启动失败'
  }
  submitting.translateNutrients = false
}
```

- [ ] **Step 9: 添加 Agent 会话状态管理和 onMounted**

将原有的 agentTasks / agentPollingMap / agentErrorMap / startAgentPolling / stopAgentPolling （第 308-498 行之间）及其相关代码保留，更新 `onMounted` 中的过滤条件：

```typescript
const AGENT_TASK_TYPES = [
  'infer_quantities', 'infer_densities',
  'usda_translate', 'unmapped_nutrient_translate',
]

onMounted(async () => {
  fetchTasks(10)

  // 加载翻译配置
  try {
    translationConfig.value = await getTranslationConfig()
    if (enabledAiProviders.value.length) {
      aiInferProvider.value = enabledAiProviders.value[0]
    }
    if (enabledTranslateProviders.value.length) {
      translateProvider.value = enabledTranslateProviders.value[0]
    }
  } catch { /* 忽略 */ }

  // 加载 USDA 统计和未映射营养素
  await loadUsdaStats()
  await loadUnmapped()

  // 恢复最近的 agent 会话
  try {
    const recent = await listSessions(20)
    const relevant = recent.filter((s) => AGENT_TASK_TYPES.includes(s.task_type))
    for (const s of relevant) {
      if (!agentTasks.value.find((t) => t.session_id === s.id)) {
        agentTasks.value.push({
          session_id: s.id,
          task_type: s.task_type,
          label: TASK_LABELS[s.task_type] || s.task_type,
          status: s.status === 'completed' ? 'success' : (s.status as any),
          created_at: s.created_at || new Date().toISOString(),
        })
      }
    }
  } catch { /* 忽略 */ }

  // 恢复轮询
  const pendingAgent = agentTasks.value.filter(
    (t) => t.status === 'pending' || t.status === 'running'
  )
  pendingAgent.forEach((t) => startAgentPolling(t.session_id))
})
```

- [ ] **Step 10: 添加 AgentTaskItem 接口和合并任务列表**

保留 `AgentTaskItem`、`ImportTaskLike`、`AgentTaskLike`、`MergedTask` 类型的定义，以及 `mergedTasks` computed 属性。将任务标签映射扩展为：

```typescript
const TASK_LABELS: Record<string, string> = {
  'infer_quantities': 'Agent 模糊量推测',
  'infer_densities': 'Agent 密度推测',
  'usda_translate': 'Agent 食材名翻译',
  'unmapped_nutrient_translate': 'Agent 营养素翻译',
}
```

确保 `mergedTasks` 模板中 v-for 的 key 使用 `'_kind' === 'import' ? 'imp-' + t.id : 'agt-' + t.session_id`。

- [ ] **Step 11: 确保 `formatTime` 和状态辅助函数存在**

保留 `taskTypeLabels`、`statusConfig`、`statusColor`、`statusIcon`、`statusLabel`、`taskRunningClass`、`formatTime` 等辅助函数。其中 `taskTypeLabels` 保留 import 任务的映射：

```typescript
const taskTypeLabels: Record<string, string> = {
  git_import: 'Git 仓库导入',
  local_import: '本地路径导入',
  upload_import: '上传导入',
  ai_quantities: 'AI 模糊量推测',
  ai_densities: 'AI 密度推测',
}
```

- [ ] **Step 12: 验证前端构建**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

```bash
cd frontend && npx vite build 2>&1 | tail -20
```

---

### Task 4: 前端 — 路由 + 侧边栏 + Dashboard

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/layout/DesktopNav.vue`（可能需要添加 admin 导航项）
- Modify: `frontend/src/views/admin/AdminDashboard.vue`

- [ ] **Step 1: 添加 `/admin/data-maintenance` 路由**

在 `frontend/src/router/index.ts` 的 `children` 数组中，在 `/admin/recipe-import`（第 127-131 行）之后添加：

```typescript
{
  path: 'admin/data-maintenance',
  name: 'admin-data-maintenance',
  meta: { adminOnly: true, title: '数据维护' },
  component: () => import('@/views/admin/DataMaintenanceView.vue'),
},
```

- [ ] **Step 2: 将 `/admin/recipe-import` 改为重定向**

将第 127-131 行的路由改为：

```typescript
{
  path: 'admin/recipe-import',
  redirect: '/admin/data-maintenance',
},
```

保留原 name 为 `admin-recipe-import` 可以不加 name，直接用 redirect。

- [ ] **Step 3: 修改 AdminDashboard.vue 的卡片**

将第 106-115 行的卡片改为：

```vue
<v-list-item
  prepend-icon="mdi-database-cog"
  title="数据维护中心"
  subtitle="菜谱导入、AI 维护、USDA 数据管理"
  to="/admin/data-maintenance"
>
  <template #append>
    <v-icon>mdi-chevron-right</v-icon>
  </template>
</v-list-item>
```

同时修改卡片标题 `title="菜谱导入"` → `title="数据维护中心"`、`subtitle="从外部来源导入菜谱数据"` → `subtitle="菜谱导入、AI 维护、USDA 数据管理"`。

- [ ] **Step 4: 验证前端构建**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

```bash
cd frontend && npx vite build 2>&1 | tail -20
```

---

### Task 5: 前端 — UsdaDataView.vue 移除翻译按钮

**Files:**
- Modify: `frontend/src/views/admin/UsdaDataView.vue`

- [ ] **Step 1: 移除食材翻译和营养素翻译的操作区域**

在 UsdaDataView.vue 的模板中，移除：
1. 「翻译食材名称」卡片（含 provider 选择器和「开始翻译」按钮）
2. 「AI 翻译未映射营养素」卡片（含 provider 选择器和按钮）

保留 USDA 统计数据、下载/上传按钮和未映射营养素列表的可折叠展示。

- [ ] **Step 2: 移除相关 script 代码**

在 `<script setup>` 中移除：
1. `translateUsda`、`translateNutrients` 的导入调用
2. `translateProvider`、`nutrientProvider` ref
3. `translating`、`translatingNutrients` ref
4. `onTranslate`、`onTranslateNutrients` 函数
5. `enabledProviders`、`enabledAiProviders` computed 属性
6. 相关的 watch

保留 `getUsdaStatistics`、`getUnmappedNutrients`、`downloadUsda`、`uploadUsda` 及相关数据和函数。

- [ ] **Step 3: 添加迁移提示**

在 USDA 统计数据卡片底部添加提示：

```vue
<p class="text-caption text-medium-emphasis mt-2">
  💡 翻译操作已迁移至「<router-link to="/admin/data-maintenance">数据维护中心</router-link>」
</p>
```

- [ ] **Step 4: 验证前端构建**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -50
```

```bash
cd frontend && npx vite build 2>&1 | tail -20
```

---

### Task 6: 端到端验证

- [ ] **Step 1: 确认后端模板注册**

```bash
curl -s http://localhost:8000/api/v1/agent/task-types | python -m json.tool
```

预期输出包含 5 个任务类型：fill_piece_weight / infer_quantities / infer_densities / usda_translate / unmapped_nutrient_translate。

- [ ] **Step 2: 前端功能验证**
1. 打开 `http://localhost:5173/admin/data-maintenance`
2. 确认页面布局：导入数据三卡 + AI 维护 + USDA 数据管理 + 统一任务列表
3. 确认两个选择器（AI 推断后端 / 翻译后端）正确加载
4. 确认四个 Agent 按钮都存在，点击后创建会话
5. 确认旧路径（非 claude_code）仍然可用
6. 确认统一任务列表显示 import 和 agent 混合任务
7. 点击 agent 任务跳转 AgentTaskConsole
8. 刷新页面后会话恢复正常

- [ ] **Step 3: 旧页面重定向验证**
1. 打开 `http://localhost:5173/admin/recipe-import` → 自动跳转到 `/admin/data-maintenance`
2. admin dashboard 中「数据维护中心」卡片链接正确

- [ ] **Step 4: USDA 页面验证**
1. 打开 `http://localhost:5173/admin/usda-data`
2. 确认翻译按钮已移除
3. 确认统计数据查看正常
4. 确认底部迁移提示链接正确

- [ ] **Step 5: 记录要点**

将实现要点记录到 `cc/` 目录的摘要文件。
