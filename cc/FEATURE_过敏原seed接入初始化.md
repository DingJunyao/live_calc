# 过敏原 seed 接入数据库初始化流程

> 完成日期：2026-07-11

## 背景

项目曾交付「按 GB 7718-2025 创建 13 个过敏原黑名单分组 + 原料映射」功能（见自动记忆 [ALLERGEN_GROUPS_SEED]），但只以**手动脚本** + 三引擎 SQL 形式存在，**从未接入数据库初始化流程**，导致空库重启后分组为空。

PG（`localhost:5432/livecalc`）实测两表均为 0 行。

根因四层（代码层确认）：

1. `init_default_data`（[main.py:46](backend/app/main.py#L46)）只塞单位/换算/地区/分类，无过敏原
2. lifespan（[main.py:199](backend/app/main.py#L199)）不调 seed
3. alembic [20260626_0001](backend/alembic/versions/20260626_0001_add_blacklist_and_allergen_groups.py) 只 `create_table`、无 INSERT 种子数据；且项目走 `create_all` 建表、不走 alembic
4. [seed_allergen_groups.py](backend/scripts/seed_allergen_groups.py) 是 `if __name__ == "__main__"` 独立脚本，全库无人 import

## 方案：抽 services 复用 + 空表自愈

**触发策略**（用户拍板）：空表自愈——`blacklist_groups` 为空才建、有数据跳过；不耦合 `first_run_init_recipes`（默认 False）。

**组件拆分（DRY）**：新建 [app/services/allergen_seed.py](backend/app/services/allergen_seed.py)，承载三样：

- `ALLERGEN_GROUPS` 常量 —— 13 组 + 原料映射，**全局唯一数据源**（从 scripts 搬入）
- `_create_groups(db) -> (created, mappings, not_found)` —— 纯创建逻辑（按名查 ID 含别名 → 建组 → 建映射 → commit），接受外部 db、不自开 session
- `ensure_allergen_groups(db) -> None` —— 幂等包装：`BlacklistGroup` count > 0 跳过，空表才调 `_create_groups`

**lifespan 接入**：[main.py](backend/app/main.py) 在批量建商品收尾（:286）之后、USDA 索引（:288）之前插入 `ensure_allergen_groups(db)`，try/except 兜底（失败只 logger.warning 不阻断启动）。排在批量建商品之后——seed 按原料名查 ID，此时 ingredients/products 已就绪、匹配率最高。

**scripts 改壳**：[scripts/seed_allergen_groups.py](backend/scripts/seed_allergen_groups.py) 瘦身为壳，import services 的 `ALLERGEN_GROUPS` + `_create_groups`，保留命令行 destructive「清空重建」行为（开发者手动重跑用）。两入口共用一份逻辑。

## 顺手修潜伏 bug：pop 破坏性

原脚本 `group_data.pop("ingredient_names")` 原地删键。脚本单次执行无碍，但 `ALLERGEN_GROUPS` 抽成模块级常量被 ensure 反复调用后，第二次起键已消失 → 匹配落空。`_create_groups` 改用非破坏性 `.get("ingredient_names", [])`。这是抽离复用的必要前置。

## 改动文件

| 文件 | 动作 | 说明 |
|---|---|---|
| [backend/app/services/allergen_seed.py](backend/app/services/allergen_seed.py) | 新建 | 数据常量 + 创建逻辑 + 幂等入口 |
| [backend/tests/services/test_allergen_seed.py](backend/tests/services/test_allergen_seed.py) | 新建 | 4 单测（空库创建/已有跳过/双调幂等/缺失容错） |
| [backend/app/main.py](backend/app/main.py) | 修改 | lifespan 插入 ensure 调用 |
| [backend/scripts/seed_allergen_groups.py](backend/scripts/seed_allergen_groups.py) | 改壳 | 复用 services，保留 destructive 命令行 |

## 验证

- 单测 4 passed（`pytest tests/services/test_allergen_seed.py`）
- compileall 三文件干净
- 后端 reload 触发 lifespan → PG 实测 `blacklist_groups=13`、`blacklist_group_ingredients=166`
- 幂等成立：reload 建一次后，独立进程再调 `ensure_allergen_groups` 输出「已存在（13 个），跳过初始化」

## 范围界定

- 表结构不变（`blacklist_groups` / `blacklist_group_ingredients` 表早建好）→ **无需 alembic / SQL 脚本**
- 不碰前端、不加新配置项、不改模型

## 遗留与注意

- 166/168：2 个原料名未匹配（库内无对应 ingredient，计入 `not_found`，正常容错）
- 无日志文件（uvicorn 输出到控制台，非文件），验证靠 DB 查询
- 命令行脚本仍可 `python -X utf8 backend/scripts/seed_allergen_groups.py` 清空重建（destructive，按需手动跑）
- 走 superpowers 全流程：brainstorming → spec（[docs/superpowers/specs/2026-07-11-过敏原seed接入初始化-design.md](docs/superpowers/specs/2026-07-11-过敏原seed接入初始化-design.md)）→ plan（[docs/superpowers/plans/2026-07-11-过敏原seed接入初始化.md](docs/superpowers/plans/2026-07-11-过敏原seed接入初始化.md)）→ executing-plans（inline，不 commit）
