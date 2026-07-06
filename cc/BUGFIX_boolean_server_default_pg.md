# PostgreSQL boolean server_default 不兼容修复

## 现象

`backend/.env` 切换到 `DATABASE_URL=postgresql://...` 后，后端启动 lifespan 执行 `Base.metadata.create_all(bind=engine)` 崩溃：

```
psycopg2.errors.DatatypeMismatch: 错误:  字段 "is_active" 类型是 boolean, 但默认表达式类型是 integer
HINT:  你需要重写或转换表达式
[SQL:
CREATE TABLE entity_densities (
        ...
        is_active BOOLEAN DEFAULT 1 NOT NULL,
        ...
)]
```

## 根因

`entity_densities` / `entity_unit_overrides` 两表的 `is_active` 字段（软删标记）在模型里写成了：

```python
is_active = Column(Boolean, default=True, nullable=False, index=True,
                   server_default=sa.text("1"))  # ← 凶手
```

`server_default=sa.text("1")` 生成的 DDL 是 `is_active BOOLEAN DEFAULT 1`：

- **SQLite**：boolean 本就是 integer 的别名，`1` 照单全收 ✅（故开发库一直没崩）
- **PostgreSQL**：严格类型校验——boolean 列的默认表达式必须是 boolean 字面量，整数 `1` 直接拒 ❌
- **MySQL**：`BOOL` 即 `TINYINT(1)`，`1` 可用 ✅

历史上 `sa.text("1")` 的写法（见 [MULTI_USER_PERMISSIONS](MULTI_USER_PERMISSIONS.md) 系列的实体单位覆盖/密度接入审核框架）是图 SQLite 顺手，没考虑 PG。

## 取证

- 错误堆栈精确定位到 `CREATE TABLE entity_densities ... is_active BOOLEAN DEFAULT 1 NOT NULL`
- `grep "server_default=sa.text\(['\"]1['\"]\)"` 命中 5 处同款：
  - [entity_density.py:24](../backend/app/models/entity_density.py#L24)
  - [entity_unit_override.py:28](../backend/app/models/entity_unit_override.py#L28)
  - [20260704_0001_add_email_config_tables.py:27](../backend/alembic/versions/20260704_0001_add_email_config_tables.py#L27)（use_tls）
  - [20260704_0001_add_email_config_tables.py:30](../backend/alembic/versions/20260704_0001_add_email_config_tables.py#L30)（enabled，`sa.text("0")`）
  - [20260629_c0e1d2f3a4b5_entity_unit_density_soft_delete.py:175,190](../backend/alembic/versions/20260629_c0e1d2f3a4b5_entity_unit_density_soft_delete.py#L175)（两处）
- 项目既定惯例 [task_templates.py:60-62](../backend/app/services/agent/task_templates.py#L60) 明确写：「布尔列……请使用 `WHERE col = true` 或 `WHERE col = false`，**不要**使用 `WHERE col = 1`……（它们在 PostgreSQL 等数据库上不兼容）」，且 [task_templates.py:89](../backend/app/services/agent/task_templates.py#L89) 的 INSERT 示例 `VALUES(..., false)`。这两处模型当初漏看了自家规矩。
- `migrate_from_bak` 路径已不存在（grep 无匹配），原始 INSERT 仅来自 task_templates（Agent 维护任务），其 INSERT 不带 `is_active` 列 → 依赖 DEFAULT 兜底。

## 修复

全部改用 `sa.text("true")` / `sa.text("false")`（三库字面量通吃）：

- **核心（解锁 create_all）**：
  - `entity_density.py:24`：`sa.text("1")` → `sa.text("true")`
  - `entity_unit_override.py:28`：`sa.text("1")` → `sa.text("true")`
- **同病预防（alembic 跑 PG 也兼容）**：
  - `20260704_0001_add_email_config_tables.py`：use_tls `"1"`→`"true"`、enabled `"0"`→`"false"`
  - `20260629_c0e1d2f3a4b5_entity_unit_density_soft_delete.py:175,190`：两处 `"1"`→`"true"`

**为何 `true` 三库通吃**：
- PostgreSQL：boolean 字面量本就是 `true` ✅
- SQLite：3.23.0（2018-04）起 `true`/`false` 作为 `1`/`0` 别名；实测 3.50.4 ✅
- MySQL：`BOOL`=`TINYINT(1)`，`true`=1 ✅

## 验证

1. `py_compile` 四个文件全过。
2. 三方言 DDL 编译（CreateTable + dialect），`is_active` 列全部产出 `DEFAULT true`：
   ```
   EntityDensity [postgresql]: is_active BOOLEAN DEFAULT true NOT NULL,
   EntityDensity [sqlite]:     is_active BOOLEAN DEFAULT true NOT NULL,
   EntityDensity [mysql]:      is_active BOOL NOT NULL DEFAULT true,
   EntityUnitOverride [postgresql]: is_active BOOLEAN DEFAULT true NOT NULL,
   EntityUnitOverride [sqlite]:     is_active BOOLEAN DEFAULT true NOT NULL,
   EntityUnitOverride [mysql]:      is_active BOOL NOT NULL DEFAULT true,
   ```
3. SQLite 运行时实测 `DEFAULT true` 解析为 `1`（True），Agent 的不带 `is_active` 列的原始 INSERT 兜得住，无回归。

## 未改动 / 不需改

- **SQL 脚本**：`backend/scripts/sql/` 下 PG 脚本本就用 `true/false`；SQLite/MySQL 脚本用 `0/1` 是各自引擎的正确惯例（SQLite boolean=integer 别名、MySQL `TINYINT(1)` 吃整数）。grep `DEFAULT [01]` 在 PG 脚本里只命中整数列（`id`/`sort_order`），未命中 boolean 列，确认 PG 脚本本就规范。
- **表结构变更**：本次字段定义未变（仍是 `Boolean + default=True + server_default`），仅修正 `server_default` 的 SQL 文本，故无需新建 alembic 迁移、无需补三引擎 SQL 脚本。
- **Python 层 `default=True`**：保留不动（ORM INSERT 兜底，与 server_default 双保险）。

## 影响

- 解锁 PostgreSQL 作为后端库的 `create_all` 初始化（用户正检验多数据库支持）。
- SQLite 开发库无影响（运行时语义不变）。
- MySQL 兼容性顺带对齐。
- 运行时：uvicorn `--reload` 检测模型 `.py` 改动自动重启重跑 lifespan `create_all`，`checkfirst=True` 跳过已建表，只补建此前崩掉的 `entity_densities`。
