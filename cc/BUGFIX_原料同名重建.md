# 修复：删除原料后无法新建同名原料

日期：2026-06-13

## 问题

原料被删除后，无法再新建同名原料（前端报「原料已存在」或后端 500 错误）。

## 根因（双重阻断）

1. **数据库层**：`ingredients.name` 字段带 `unique=True`，DB 上为 `CREATE UNIQUE INDEX ix_ingredients_name ON ingredients (name)`。原料删除是**软删除**（仅置 `is_active=False`，记录与 name 仍留在表中），因此 DB 层 INSERT 同名记录必然触发唯一约束冲突。
2. **应用层**：创建/更新接口的重名检查**未过滤 `is_active`**，先于 DB 拦截并返回「已存在」。前端创建走 `ingredient_extended`、删除走 `nutrition`，两套并存路由都有此问题。

参考模式：`Product.name` 仅 `index=True`、无 `unique=True`，纯应用层校验，故商品软删除后可重建同名。原料与之对齐即可。

## 修复方案

去掉 `name` 的 DB 唯一约束（保留普通索引），重名检查只针对活跃记录（`is_active == True`）。

## 修改清单

1. **模型** `backend/app/models/nutrition.py`：`name` 去掉 `unique=True`，改为 `name = Column(String(200), nullable=False, index=True)`。
2. **应用层重名检查加 `is_active` 过滤**（统一模式，共 4 处）：
   - `backend/app/api/ingredient_extended.py`（create、update）
   - `backend/app/api/nutrition.py`（create、update）
   - 改动：`filter(Ingredient.name == name)` → `filter(Ingredient.name == name, Ingredient.is_active == True)`
3. **数据库结构变更**：`ix_ingredients_name` 由唯一索引降级为普通索引。
   - 多数据库 SQL 脚本：`backend/scripts/migrations/drop_unique_constraint_on_ingredients_name.{sqlite,mysql,pgsql}.sql`
   - alembic 迁移：`backend/alembic/versions/20260613_0001_drop_unique_constraint_on_ingredients_name.py`

## 数据库执行说明（重要）

- 本项目的 alembic **版本链预先断裂且 `alembic_version` 表为空**（数据库实际由 `Base.metadata.create_all()` 建成，alembic 从未真正使用），故 `alembic upgrade head` 不可行。
- 开发库 `backend/data/livecalc.db` 的索引变更已用 Python `sqlite3` 直接执行（`DROP INDEX` + `CREATE INDEX`），等效于迁移的 `upgrade()`。
- 部署到 MySQL/PostgreSQL 时，执行对应 `drop_unique_constraint_on_ingredients_name.<db>.sql` 脚本即可。
- 已存在的 5 条 `is_active=0` 占位记录无需清理，约束去除后即可新建同名原料。

## 附带修复

- `backend/alembic.ini` 的中文注释已改为 ASCII（英文）。原因：Python 3.14 的 `configparser` 用 `encoding="locale"`（Windows = GBK）读取 ini，UTF-8 中文注释导致 `UnicodeDecodeError`，使 alembic 完全无法加载。`PYTHONUTF8=1` 无效（`locale.getencoding()` 不受 UTF-8 模式影响）。ASCII 化后 alembic 可正常加载（但版本链断裂问题仍待后续单独修复）。

## 待办（建议后续处理）

- 修复 alembic 版本链的 `revision`/`down_revision` 命名不一致（如 `20260611_0001` 的 `down_revision` 用了长形式 `20260609_0001_add_is_open_to_merchants`，而 `20260609` 实际 `revision='20260609_0001'`；更早的 `20260318→20260314_0001`、`20260312→7408e388` 引用了不存在的 revision）。此问题独立于本次 bug，需系统核对全链。

## 验证

- `py_compile` 全部修改文件通过。
- DB 端到端：取软删除记录（如 id=645「丝瓜」），插入同名活跃记录成功（唯一约束已解除），用 `lastrowid` 精确清理，记录数恢复原值，无数据污染。
- 应用层：4 处重名检查均含 `Ingredient.is_active == True`，活跃原料间重名仍被正确拦截。
