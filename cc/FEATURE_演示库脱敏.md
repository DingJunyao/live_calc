# 演示库脱敏脚本 desensitize_demo_db.py

## 背景

`backend/data/livecalc.db` 当前是后端实际在用的库（`.env` `DATABASE_URL=sqlite:///./data/livecalc.db`，PG/MySQL 注释掉了——**注意不是自动记忆 [backend-uses-postgresql] 所说的 PG，.env 已改回 SQLite，记忆过时**）。需把它做成演示版：脱敏 + 精简到 `admin`/`test` 两用户，密码统一 `123456`。

## 现状探查（执行前）

- users 共 13 条（id 1、5、12-22）
- **id=1 admin**：4901 条业务引用（价格记录 2370 / 商品 833 / 菜谱 363 / 原料 115 / 推荐 18 / 黑名单 24 / 商家 8 / 收藏 …）——全部业务数据归属它
- **id=12 testuser→test**：0 引用，纯空账号
- **其余 11 个（5、13-22）**：业务表零引用。67 条外键都 `ON DELETE NO ACTION` 但全部指向 admin，待删用户零引用 → 可放心硬删，无孤儿
- **id=2（早已删除的用户）**：审计字段残留 3 条（`ingredients.created_by` / `products.created_by`+`updated_by`）。审计字段在 [BUGFIX_audit_field_pg_fk_violation] 已去掉外键约束，指向幽灵用户也无害
- `phone` 全空、无散落 PII（`merchants.address` 等是业务地址，非用户隐私）

## 关键坑：前端 SHA256 预处理（差点翻车）

首轮脱敏用 `bcrypt("123456")` 存储，脚本内 bcrypt 自检通过就以为成了。端到端 `POST /auth/login` 返回 422 要 `password_hash` 字段，顺藤摸出真实链路：

- 前端 [crypto.ts:10](../frontend/src/utils/crypto.ts#L10) `hashPassword = crypto-js SHA256().toString()`（小写 hex）
- 后端 [schemas/auth.py UserLogin](../backend/app/schemas/auth.py#L34) 字段叫 `password_hash`，注释「前端已 SHA256 加密」
- 后端 [auth.py:192](../backend/app/api/auth.py#L192) `verify_password(user_data.password_hash, user.password_hash)` —— 存的是 `bcrypt(SHA256_hex(明文))`，登录比对同口径
- 直接存 `bcrypt("123456")` 的话，前端登录传 `SHA256("123456")`，bcrypt 解出的明文 ≠ SHA256 串 → **演示库密码根本登不上**

修正：脚本加 `_sha256_hex()` 对齐 crypto-js，存 `bcrypt(SHA256("123456"))`；自检 `assert` 也改用 SHA256 口径，避免「bcrypt verify 通过但实际登不上」的假绿。

**教训**：改密码类脱敏必须端到端登录验证。`bcrypt.checkpw` 通过 ≠ 能登录，中间可能隔着前端预处理层。这正是 `superpowers:verification-before-completion` 的价值——脚本自检全绿也差点交付一个登不上的演示库。

## 脚本 backend/scripts/desensitize_demo_db.py

幂等、带时间戳备份、原子事务：

1. `shutil.copy2` 备份 → `livecalc.db.bak_desensitize_<ts>`
2. 事务内（`with con:` 自动 commit / 异常回滚）：
   - `UPDATE users SET password_hash=bcrypt(SHA256("123456")), token_version=0`
   - 确认 admin/test 的 `username`/`email`（不依赖现状）
   - `DELETE FROM users WHERE id NOT IN (1,12)`
   - 清 id=2 审计残留 → admin(1)
3. 验证：列 users + `bcrypt.checkpw(SHA256(pw), 哈希)` + 引用完整性复查（67 条真用户引用列不得指向已删用户）+ VACUUM

用法（在 backend/ 目录下）：

```
../.venv/Scripts/python.exe scripts/desensitize_demo_db.py [db_path]
```

默认 `data/livecalc.db`。用根目录 `.venv`（有 bcrypt 5.0.0），不是 `backend/.venv`。

## 执行结果（2026-07-18）

- 改前 13 → 改后 **2**（admin / test）
- 11 个零引用用户硬删，引用残留复查 **0**
- id=2 残留清理 3 条
- 两账号 `verify(sha256·123456)=True`
- 端到端 `POST /api/v1/auth/login`（`username` + `password_hash=SHA256 hex`）：admin / test 均 **HTTP 200 + 拿到 JWT bearer**
- 备份：
  - `livecalc.db.bak_desensitize_20260718_201722`（首轮错误版，bcrypt 明文）
  - `livecalc.db.bak_desensitize_20260718_202025`（修正版，最终库的前身；如需回滚用这个）

## 决策记录（用户拍板）

- 操作目标：**直接改 livecalc.db**（先备份），不另存 demo 文件
- test 账号：**保持空**（演示新用户视角），admin 持全部业务数据
- id=2 残留：**一并清理**

## 备注

- 业务数据（菜谱 / 价格 / 商品 / 原料 / 地图 / 推荐 …）原样保留作为演示内容，未动
- `token_version` 归 0：admin 旧 session（原 ver=2）已失效，需用 `123456` 重新登录（演示库期望行为）
- 后端 SQLite 连接是文件级的，改完即时生效（已 200 验证），无需重启服务
- 本次纯 DML 数据脱敏，**非 DDL 表结构变更**，无需 alembic / 四引擎 SQL 脚本
