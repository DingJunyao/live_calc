# 共享转型 schema 漂移修复（units.is_standard / recipes.is_public / merchants.user_id）

## 现象
后端启动报 `sqlite3.OperationalError: no such column: units.is_standard`（SQLAlchemy 查 `units` 全字段 SELECT 时炸在 `is_standard`）。

（注：此前还有一个无关报错——`pydantic ValidationError: Extra inputs are not permitted`，指向 `VITE_DATA_REPO_IMAGE_BASE`/`VITE_REQUEST_TIMEOUT`/`VITE_LONG_REQUEST_TIMEOUT`。根因是 [config.py](backend/app/config.py) 的 `Settings`（pydantic-settings）`extra` 为 forbid，而 `backend/.env` 混入了这三个**前端**变量。用户已自行删除 `.env` 中这三个变量解决；更稳妥的根因修法是把 Settings 的 `extra` 改为 `ignore`，避免以后 `.env` 多放前端变量再崩，本次未改。）

## 根因
开发库 [livecalc.db](backend/data/livecalc.db) 由 `Base.metadata.create_all()` 建库，**从未走 alembic**（无 `alembic_version` 表，查它直接 `no such table`）。`create_all` 只建**新表**，不碰「给已有表加列 / 改约束」的 ALTER，故迁移 [20260627_0002_shared_data_transform.py](backend/alembic/versions/20260627_0002_shared_data_transform.py) 中三处「改老表」变更全部漂移：

| 迁移变更 | 库中状态 | 影响 |
|---|---|---|
| `units.is_standard` 新列 | 缺失 | 启动 SELECT 必崩（即本报错） |
| `recipes.is_public` 新列 | 缺失 | 同 SELECT 必崩（修好上一项后下一个轮到） |
| `merchants.user_id` 改可空 | 仍 NOT NULL | 语义已改「拥有者→录入者」，启动暂不崩，写入空值会炸 |

同批两张**新表**（`user_merchant_favorites`、`product_merchant_price_summary`）及 0001 的 `change_proposals` 因 create_all 建表机制已落地，未漂移——印证「只漏 ALTER 老表」的判断。

代码层面（迁移文件、[SQL 脚本](backend/scripts/sql/20260627_shared_transform_sqlite.sql)）均正确，**无需改动，纯开发库欠账**。

为何不能 `alembic upgrade head`：库无 `alembic_version`（不知当前版本），且 upgrade 的 `create_table('user_merchant_favorites'/'product_merchant_price_summary')` 会因两表已存在而报 `table already exists`。

## 修复（直接补开发库）
操作前已备份 `livecalc.db.bak_20260629_103713`。

1. `ALTER TABLE units ADD COLUMN is_standard BOOLEAN NOT NULL DEFAULT 0`
2. `ALTER TABLE recipes ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT 0`
3. `merchants.user_id` 改 nullable：用 alembic `batch_alter_table` 离线执行（SQLite 不支持 ALTER COLUMN，需表重建，交给成熟的 alembic 实现免手写易错 SQL）。用法：`engine.connect()` → `MigrationContext.configure(conn)` → `Operations(ctx).batch_alter_table('merchants', recreate='auto')` → `alter_column('user_id', existing_type=Integer, nullable=True)` → `commit()`，**不依赖 alembic_version 表**。

## 验证
- 三处变更生效：`is_standard`/`is_public` 列存在；`merchants.user_id` notnull `1→0`。
- `merchants` 表完整性：空表（0 行），行数/ID 求和与备份一致，零数据风险。
- 索引保留：`ix_merchants_id`、`ix_merchants_user_id`（batch 表重建未丢）。
- 模拟 ORM SELECT（报错原句字段）全跑通：`units(id,is_standard,is_common,display_order)`、`recipes(id,is_public)`、`merchants(id,user_id)`。

## 遗留与建议
- **库不走 alembic 的通病**：可能还有更早的「ALTER 老表」类迁移同样漂移（如某表的 is_open/is_active/token_version 等，凡建库后又加列的）。若后端启动后再报 `no such column` 或约束冲突，同法（ADD COLUMN / batch_alter_table）补即可。
- （可选）补完后可 `alembic stamp head` 让开发库纳入 alembic 版本管理，使未来 `alembic upgrade head` 可用；但需**先确认无其他历史漂移**——stamp 会把当前状态标为最新，掩盖未补的列。
- 单元/集成测试未跑（本次为开发库环境修复，非代码变更）。

## 配套：完善 SQLite 脚本为可直接手动执行
原 [20260627_shared_transform_sqlite.sql](backend/scripts/sql/20260627_shared_transform_sqlite.sql) 把 `is_public`/`is_standard` 加列注释掉、`merchants.user_id` 改约束省略（标注「走 alembic」），与「项目不用 alembic」矛盾——手动执行跑不全。改为完全自包含、不依赖 alembic：

- 放开 `recipes.is_public`、`units.is_standard` 的 `ADD COLUMN`（一次性，注释标注已应用请跳过）。
- `merchants.user_id` 改 nullable 补 SQLite 官方「表重建」流程（CREATE 新表→INSERT 复制→DROP 旧表→RENAME），`PRAGMA foreign_keys=OFF/ON` 在事务外切换，索引用 `IF NOT EXISTS` 重建。
- MySQL / PostgreSQL 版本来就直接写了 `ALTER`（不依赖 alembic），无需改。

验证：手搓模拟旧结构测试库（merchants 塞 2 条数据 + NOT NULL `user_id`、无 `is_standard`/`is_public`），executescript 全程无报错；表重建后 merchants 2 条数据完整保留、9 列齐全、索引在、`user_id` 可空；加列/建表/收藏回填全部正确。测试库已清理。

alembic 迁移、模型、MySQL/PG 脚本均未改。
