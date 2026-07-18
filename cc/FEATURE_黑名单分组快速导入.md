# 黑名单分组：跟随菜谱导入初始化 + 管理页「快速导入过敏原」按钮

## 背景（两个相关问题）

1. **启动初始化顺序错位**：[main.py:289-293](backend/app/main.py#L289) 的 `ensure_allergen_groups` 原本在 `FIRST_RUN_INIT_RECIPES` 判断**块外**——`FIRST_RUN_INIT_RECIPES=false`（不导入菜谱/原料）时也会执行，结果原料还没入库就建了 13 个**空壳分组**（分组定义在、原料映射为 0，当前开发库正是此状态）。正确顺序应是「菜谱导入 → 原料入库 → 再建过敏原分组映射」。

2. **无手动补全入口**：`ensure_allergen_groups` / `ensure_email_templates` 这类 lifespan seed 函数都只有启动调用、**没有对应管理 API**。false 启动没建分组、或空壳想补映射时，管理员无处下手。

## 用户拍板的决策
- **「未导入」判断**：13 个标准分组（按 [ALLERGEN_GROUPS](backend/app/services/allergen_seed.py#L19) 的 name）中，任一不存在（含软删）或存在但原料映射数为 0 → 显示按钮。
- **UI 位置**：黑名单分组管理页**顶部 v-alert 提示条 + 按钮**。

## 修复（4 处改动，无表结构变更）

### 1. 服务层 — [allergen_seed.py](backend/app/services/allergen_seed.py)
保留 `ALLERGEN_GROUPS` / `_create_groups` / `ensure_allergen_groups` 不动，新增两函数：
- **`upsert_allergen_groups(db) -> dict`**：按钮/补全核心。遍历 ALLERGEN_GROUPS，分组按 `name` 查**含软删**（避免撞 name unique）：不存在则建，存在且软删则**复活（不改 display_order，尊重管理员排序调整）**。原料映射复用本会话 [export.py `_import_blacklist_groups`](backend/app/services/importer/importers/export.py) 范式——按 `(group_id, ingredient_id)` 查含软删，软删复活、不存在才建；原料按 name+别名匹配。返回 `{created, reactivated, mapped, not_found}`。
- **`need_allergen_seed(db) -> dict`**：状态判断。查 **`is_active=True`** 的标准分组（软删算缺失）+ 各自 `is_active=True` 映射数。返回 `{needed, total, existing, with_mappings, missing_groups, empty_groups}`。

### 2. lifespan — [main.py](backend/app/main.py)
把 `ensure_allergen_groups` 调用从块外**移进 `first_run_init_recipes` 的 else 分支末尾**（菜谱导入之后）：
- `FIRST_RUN_INIT_RECIPES=false` → 整个 else 跳过 → 不碰黑名单分组 ✓
- `true` + 首次 → 菜谱/原料导入后建分组 ✓
- `true` + 已初始化 → `ensure` 幂等（空表才建；已有跳过，不动管理员数据）

**lifespan 用 `ensure`（保守，不自动改管理员已有分组）、按钮用 `upsert`（主动补全）**——职责分离。

### 3. API — [blacklist_groups.py](backend/app/api/blacklist_groups.py)
`blacklist_group_admin_router`（prefix `/api/v1/admin`）加两端点，均 `get_current_admin_user` 鉴权：
- `GET /admin/blacklist-groups/allergens-status` → `need_allergen_seed(db)`
- `POST /admin/blacklist-groups/seed-allergens` → `upsert_allergen_groups(db)`，返回 `{message, stats}`

### 4. 前端 — [BlacklistGroupsView.vue](frontend/src/views/admin/BlacklistGroupsView.vue)
分组列表前加 `v-alert v-if="allergenStatus.needed"`（info/tonal/closable，文案点出缺失/空映射数）+ 内嵌 `v-btn`「快速导入过敏原分组」（`mdi-shield-sync`、loading）。script 加 `allergenStatus`/`seedingAllergens` ref + `loadAllergenStatus`/`seedAllergens`；`onMounted` 改 `Promise.all([loadGroups(), loadAllergenStatus()])`。

## 闭环验证（四种场景）
| 场景 | lifespan | need | 按钮 |
|---|---|---|---|
| `false` 启动（空库） | 不执行 | needed=true | 显示 → 点击 upsert 导入 |
| `true` 首次启动 | ensure 建 13 组+映射 | needed=false | 不显示 |
| 空壳库（当前开发库：13 组映射空） | ensure 跳过（count>0） | needed=true（映射空） | 显示 → 点击补映射 |
| 正常库（13 组+映射全） | ensure 跳过 | needed=false | 不显示 |

## 关键设计要点
- **复用导入端 upsert 范式**：`(group_id, ingredient_id)` 查含软删 → 复活 or 新建，避免撞 unique（对齐 [API add_ingredients_to_group](backend/app/api/blacklist_groups.py#L146) 与本会话导入端）。
- **尊重管理员已有数据**：upsert 不改已存在分组 `display_order`；lifespan 用 ensure 不自动改已有分组；软删的分组 upsert 会复活（符合「导入」语义，管理员故意删可改名规避）。
- **need 基于 is_active=True 分组**：软删分组对用户不可见，算「缺失」，语义更准。

## 验证
- `py_compile` 三后端文件过。
- 临时 SQLite 库测试全断言通过：空表 need needed=true；首次 upsert created=13/mapped=5（5 原料覆盖 5 组）；二次 upsert 幂等（0/0/0）；软删蛋类分组+鸡蛋映射后 need 算缺失、upsert reactivated=1/mapped=1 复活。
- 前端 build 通过（31.40s，precache 128 entries 一致）。

## 教训
- lifespan seed 函数的位置要看清是否在条件块内——「块外」会让它无视开关永远执行，建出空壳数据。
- seed 类初始化缺管理 API 时，管理员无法自助补救；给 lifespan seed 配一个 upsert 端点 + 显隐判断，是闭环标配。
- 软删 + unique 约束的表，upsert 必须「查含软删」，否则撞约束（与本会话导入端同款范式）。

注：当前开发库 `blacklist_group_ingredients` 表空（seed 名字匹配问题）——点按钮即可按库内现有原料名补映射；若库内原料名与 ALLERGEN_GROUPS 的 ingredient_names 对不上，补出来仍可能少映射，那是数据问题非逻辑问题。
