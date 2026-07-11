# 过敏原 seed 接入数据库初始化流程 — 设计文档

> 日期：2026-07-11
> 状态：待实现

## 背景

项目曾交付「按 GB 7718-2025 创建 13 个过敏原黑名单分组 + 原料映射」的功能，但仅以**手动脚本**（`backend/scripts/seed_allergen_groups.py`）和三引擎 SQL 脚本的形式存在，**从未接入数据库初始化流程**。

现状（PG `localhost:5432/livecalc` 实测）：

| 表 | 行数 |
|---|---|
| `blacklist_groups` | 0 |
| `blacklist_group_ingredients` | 0 |

根因四层（均已代码层确认）：

1. `init_default_data`（[main.py:46](backend/app/main.py#L46)）只塞单位/换算/地区/分类，无过敏原
2. lifespan（[main.py:199](backend/app/main.py#L199)）不调 seed
3. alembic [20260626_0001](backend/alembic/versions/20260626_0001_add_blacklist_and_allergen_groups.py) 只 `create_table`、无 INSERT 种子数据；且项目走 `create_all` 建表、不走 alembic
4. [seed_allergen_groups.py](backend/scripts/seed_allergen_groups.py) 是 `if __name__ == "__main__"` 独立脚本，全库无人 import/调用

## 目标

将过敏原分组种子数据接入 lifespan 启动初始化，使**空数据库首次启动自动创建** 13 个分组及原料映射，且满足：

- **幂等**：已有数据不重复创建
- **自愈**：分组被清空后重启自动重建
- **不耦合**菜谱导入开关（`first_run_init_recipes` 默认 False，不应影响本功能）

## 设计

### 1. 组件拆分（DRY）

新建 `backend/app/services/allergen_seed.py`，承载三样东西：

**`ALLERGEN_GROUPS` 常量**
13 个分组定义（`name` + `display_order` + `ingredient_names` 列表），从 `scripts/seed_allergen_groups.py` 原样搬入。全局唯一数据源，模块级常量。

**`_create_groups(db: Session) -> tuple[int, int, list[str]]`**
纯创建逻辑，接受外部传入的 db session（**不自开 session**）。返回 `(created_count, mapping_count, not_found)`。流程：

- 构建 `name → id` 查找表（含 `Ingredient.aliases` 别名）
- 遍历 `ALLERGEN_GROUPS`，按名查 ID、去重、建 `BlacklistGroup`、建 `BlacklistGroupIngredient` 映射
- `db.commit()`
- **关键约束**：读取 `ingredient_names` 用非破坏性方式（`data.get("ingredient_names", [])`），**不得用 `.pop()`**

**`ensure_allergen_groups(db: Session) -> None`**
幂等包装，供 lifespan 调用：

```python
def ensure_allergen_groups(db):
    existing = db.query(BlacklistGroup).count()
    if existing > 0:
        logger.info(f"过敏原分组已存在（{existing} 个），跳过初始化")
        return
    created, mappings, not_found = _create_groups(db)
    logger.info(
        f"过敏原分组初始化完成：{created} 组，{mappings} 条映射，未匹配 {len(not_found)} 条"
    )
```

### 2. scripts 改造为壳

`backend/scripts/seed_allergen_groups.py` 瘦身：

- `from app.services.allergen_seed import ALLERGEN_GROUPS, _create_groups`
- 保留「清空重建」命令行行为：先 `delete()` 清空 `BlacklistGroupIngredient` + `BlacklistGroup`，再调 `_create_groups`
- 保留 `os.environ.setdefault('DATABASE_URL', ...)` + 自开 `SessionLocal`（命令行场景需要）
- 保留 `if __name__ == "__main__"` 入口和打印输出

命令行脚本（destructive）与 lifespan 的 ensure（幂等）互不干扰，各取所需。

### 3. lifespan 接入点

在 [main.py:286](backend/app/main.py#L286)（批量建商品收尾）之后、[main.py:288](backend/app/main.py#L288)（USDA 索引加载）之前，插入：

```python
# 确保过敏原黑名单分组存在（空表才创建，幂等，失败不阻断启动）
try:
    from app.services.allergen_seed import ensure_allergen_groups
    ensure_allergen_groups(db)
except Exception as e:
    logger.warning(f"过敏原分组初始化失败: {e}")
```

**位置理由**：必须排在批量建商品之后——seed 按原料名查 ID，此时 `ingredients` 与 `products` 已就绪，匹配率最高。不放进 `first_run_init_recipes` 分支，因该开关默认 False 会导致永不执行，违背「初始化即有」目标。

与同段 USDA 索引、执行器注册采用一致的 try/except 风格——失败只告警、不阻断启动。

### 4. 顺手修复：pop 破坏性（抽离复用的必要前置）

原 [scripts/seed_allergen_groups.py:192](backend/scripts/seed_allergen_groups.py#L192) 的 `group_data.pop("ingredient_names")` 原地删键。脚本单次执行无碍，但 `ALLERGEN_GROUPS` 抽成模块级常量、被 `ensure` 反复调用后，第二次起 `ingredient_names` 键已消失 → 匹配落空。`_create_groups` 内改为非破坏性读取。

## 范围界定（不碰）

- 表结构不变（`blacklist_groups` / `blacklist_group_ingredients` 表已存在）→ **无需 alembic / SQL 脚本**
- 不碰前端
- 不加新配置项（不加 `FIRST_RUN_INIT_ALLERGENS`）
- 不改 `BlacklistGroup` / `BlacklistGroupIngredient` 模型

## 测试策略

新增单测，覆盖：

1. 空库 → `ensure_allergen_groups` 建出 13 组 + 映射
2. 已有数据 → 跳过（count 不变）
3. 连续两次调用 → 第二次无副作用（幂等）
4. `_create_groups` 对缺失原料容错（计入 `not_found`，不抛错）

测试依赖：需 `ingredients` 表有数据才能验证名称匹配，用 fixture 预置若干原料（或最小数据集），不依赖完整菜谱导入。

## 验证标准

- 后端 `py_compile` / `compileall` 通过
- 单测全过
- 重启后端（PG 空表）→ 日志打印「过敏原分组初始化完成：13 组」
- DB 查询 `blacklist_groups` = 13、`blacklist_group_ingredients` > 0
- 再次重启 → 日志「已存在，跳过」，数据不变（幂等）
- 命令行 `python -X utf8 backend/scripts/seed_allergen_groups.py` 仍可清空重建（destructive 行为保留）
