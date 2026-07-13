# BUGFIX：邮件模板 seed 接入初始化

## 现象

`email_templates` 表在数据库中为空（3 条默认模板 `proposal_submitted` / `proposal_approved` / `proposal_rejected` 一条都没有）。后果是 [email_service.send_template_async](../backend/app/services/email_service.py#L67) 查不到模板，所有「提议提交/通过/驳回」的审核通知邮件被静默跳过（仅打 warning log，不报错、不发邮件）。

## 根因

与 [FEATURE_过敏原seed接入初始化](FEATURE_过敏原seed接入初始化.md) **完全同构**——「默认数据只在 alembic INSERT，但项目走 create_all、lifespan 没兜底」。

四层根因：

1. `email_templates` 表由 `Base.metadata.create_all()` 建表（[main.py:206](../backend/app/main.py#L206)），表结构没问题。
2. 3 条默认模板的数据只写在两处：
   - alembic 迁移 [20260704_0001_add_email_config_tables.py:47-80](../backend/alembic/versions/20260704_0001_add_email_config_tables.py#L47) 的 `op.execute("INSERT INTO email_templates ...")`
   - 手动 SQL 脚本 [20260704_add_email_tables_*.sql](../backend/scripts/sql/)
3. 本项目**走 create_all、不走 alembic**（过敏原 / 共享转型那几关已反复证实，开发库无 `alembic_version` 表），create_all 只建表、**不执行 INSERT**。手动 SQL 脚本也没人在 create_all 路径下跑。
4. [main.py](../backend/app/main.py) 的 `init_default_data` 只塞单位/分类（[:46](../backend/app/main.py#L46)），`lifespan` 里只接了 `ensure_allergen_groups`（[:290](../backend/app/main.py#L290)），**邮件模板 seed 零接入**（grep `email_template`/`EmailTemplate`/`smtp`/`template` 在 main.py 全文零匹配）。

结果：表建好了、数据从没插过。

## 修复

照搬过敏原 seed 的成熟模式（唯一数据源 + lifespan 幂等 ensure + 失败不阻断启动），改动 3 个文件：

### 1. 新建 [email_template_seed.py](../backend/app/services/email_template_seed.py)（唯一数据源）

- 模块级常量 `EMAIL_TEMPLATES`（3 条默认模板的 key/name/subject/body_html/description），数据从 alembic 迁移原样抽取，保持一致。
- `_create_templates(db)`：按 key 逐个补齐缺失模板，返回新增条数。
- `ensure_email_templates(db)`：幂等入口，仅补缺失项。

**幂等策略取舍**：用「按 key 逐个补齐」而非过敏原的「count>0 跳过」。原因——模板可被管理员经 `PUT /admin/email-config/templates/{key}`（[email_config.py:92](../backend/app/api/email_config.py#L92)）编辑，按 key 补齐既能保护管理员修改（已存在 key 一律不动）、又能在中途失败后重启补齐缺失项（count>0 跳过会漏补）。

**注意**：`body_html` 字符串必须用普通字面量（隐式拼接），**不能用 f-string**——模板内是 `${var}`（Python `string.Template` 语法，与 [email_service.send_template_async](../backend/app/services/email_service.py#L70) 的 `safe_substitute` 对齐），f-string 会把 `${}` 当成命名插值报错。

### 2. [main.py](../backend/app/main.py) lifespan 接入

在 `ensure_allergen_groups` 块之后（[:294](../backend/app/main.py#L294) 之后）追加同结构的 try/except 块调用 `ensure_email_templates(db)`，失败仅 warning、不阻断启动（与过敏原、USDA 索引、提议执行器注册等一致）。

### 3. 新增 [test_email_template_seed.py](../backend/tests/services/test_email_template_seed.py)

3 个测试，复用 `db_session` fixture（与 `test_allergen_seed.py` 同构）：
- `test_ensure_creates_templates_when_empty`：空表 → 建 3 条，key 集合 + subject 占位符正确
- `test_ensure_preserves_existing_and_fills_missing`：预置 1 条被「编辑」过的模板 → ensure 后该条内容不被覆盖、总数补到 3
- `test_ensure_idempotent_on_double_call`：双调幂等

## 验证

- `py_compile` 三文件通过
- `pytest tests/services/test_email_template_seed.py` → 3 passed
- 无表结构变更（`email_templates` 表早由 create_all 建好，模板数据属业务数据非 schema 变更，无需新 alembic / SQL 脚本）

## 遗留与注意

- **后端 reload 后自动生效**：用户已启动自动重载后端服务，`main.py` 改动触发 reload → lifespan 重新执行 → `ensure_email_templates` 实际往 PG 插入 3 条模板。这是修复预期行为。若 reload 因 `__pycache__` 缓存未触发，手动重启后端即可。
- **既有库兼容**：若某个库此前手动跑过 `20260704_add_email_tables_*.sql` 已有模板数据，ensure 会识别到已存在 key 跳过、不覆盖；走 alembic 的库本就有 INSERT，ensure 同样跳过。三条路径互不冲突。
- 与 [[FEATURE_过敏原seed接入初始化]] 同源问题模式，后续若再发现「alembic 里有 INSERT 但 create_all 路径漏」的默认数据（如其他 seed），按同一套模式补齐即可。
