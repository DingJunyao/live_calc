# 邀请码 schema 漂移修复

## 现象
创建邀请码报错：
```
sqlite3.OperationalError: no such column: invite_codes.used_count
```
栈定位 [invite_codes.py:47](../backend/app/api/invite_codes.py#L47) 的 `db.query(InviteCode).filter(InviteCode.code == code_str).first()`。

## 根因
开发库 `backend/data/livecalc.db` 的实际 schema 与 `alembic_version` 漂移：
- `alembic_version = 20260622_0003`（alembic 认为已是 head）
- 0002 迁移 [20260622_0002](../backend/alembic/versions/20260622_0002_add_system_config_and_enhance_invite_codes.py) 里 `create_table('system_config')` 落地了，但 `batch_alter_table('invite_codes')`（used→used_count + max_uses）**没落地**，invite_codes 表仍停在旧 `used` 列。
- 后果：`alembic upgrade head` 认为 nothing to do，修不了；模型查 `used_count` 时数据库无此列。

模型 / 迁移文件 / 三份 SQL 脚本本身都正确且已提交，**纯数据库环境漂移**，代码零改动。

## 修复
不改代码。直接补 invite_codes 两列（与已提交的 [sqlite 脚本](../backend/scripts/sql/20260622_user_and_invite_code_enhancement_sqlite.sql) 一致）：
```sql
ALTER TABLE invite_codes RENAME COLUMN used TO used_count;
ALTER TABLE invite_codes ADD COLUMN max_uses INTEGER;
```
- 操作前备份 `backend/data/livecalc.db.bak_used_count`（确认无误后可删）
- 存量 `used` 是 BOOLEAN(0/1)，改名 `used_count` 后语义兼容（0 次 / 1 次），无需迁数据
- `used_count` 列类型声明保留 BOOLEAN 字样（rename 不改类型），SQLite 类型亲和性存 INTEGER 无碍，`used_count += 1` 正常

## 验证
- `PRAGMA table_info(invite_codes)`：`used_count` + `max_uses` 在位
- ORM 层：模拟 [invite_codes.py:47](../backend/app/api/invite_codes.py#L47) 查询不再报错；插入 `used_count=0 / max_uses=None` flush 成功，`is_exhausted=False`；rollback 无残留

## 预防（schema 漂移识别套路）
- 现象特征：`no such column` + alembic 版本号已在 head → 优先怀疑版本号与实际表结构不一致
- 核对方法：`PRAGMA table_info(<表>)` 看列 vs 模型定义；`SELECT version_num FROM alembic_version`
- 慎用 `alembic stamp` 跳过实际执行；SQLite 下 `batch_alter_table` 中途失败可能留下 DDL 已部分提交（create_table 成功、alter_table 没生效）的不一致态
