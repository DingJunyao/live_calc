# 审计字段外键致 PG 空库导入违反外键约束

## 现象

修复 [boolean server_default](BUGFIX_boolean_server_default_pg.md) 后 `create_all` 通过，PG 上启动 lifespan 导入初始数据时崩：

```
psycopg2.errors.ForeignKeyViolation: 插入或更新表 "products" 违反外键约束 "products_created_by_fkey"
DETAIL: 键值对(created_by)=(1)没有在表"users"中出现.
[SQL: INSERT INTO products (..., created_by, updated_by, ...) VALUES (..., %(created_by)s, ...)]
[parameters: {'name': '西葫芦', 'ingredient_id': 2, 'created_by': 1, 'updated_by': 1, 'is_active': True, ...}]
```

## 根因

两层叠加：

1. **外键存在**：`AuditMixin.created_by/updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)`（[base_model.py:13-14](../backend/app/core/base_model.py#L13)、[:30-31](../backend/app/core/base_model.py#L30)），所有继承 AuditMixin 的模型（Product/Recipe/Ingredient/Unit/NutritionData/...）的审计字段都带外键。
2. **导入写死 user_id=1**：启动导入流程假设 users 表已有 id=1 用户——
   - [main.py:236](../backend/app/main.py#L236) `local_import(db, local_path, user_id=1)`、[:243](../backend/app/main.py#L243) `import_from_git_repo(db, user_id=1)`
   - [main.py:270-271](../backend/app/main.py#L270) 批量建商品 `created_by=1, updated_by=1`
   - [howtocook.py:149-150](../backend/app/services/importer/importers/howtocook.py#L149) 导入同名商品 `created_by=self.user_id, updated_by=self.user_id`
   - [howtocook.py:207](../backend/app/services/importer/importers/howtocook.py#L207) `Recipe(user_id=self.user_id)`

SQLite 开发库里 user_id=1 是真实存在的历史用户 + SQLite 外键默认 OFF 不校验，故从不暴露；PG 是**全新空库**（users 表无任何记录）+ 外键强制校验，导入立即触发 `ForeignKeyViolation`。

**为何崩在 products 不在 ingredients**：[howtocook.py:131-138](../backend/app/services/importer/importers/howtocook.py#L131) 导入 Ingredient 时**未设** created_by（NULL，nullable 合法），紧接着 [:146-152](../backend/app/services/importer/importers/howtocook.py#L146) 建同名 Product 时 `created_by=self.user_id`（=1）才触发外键。日志的 `name='西葫芦' ingredient_id=2` 与该路径完全吻合。

## 决策（用户拍板）

> 约定创建者、修改者填 0。不搞这方面的外键。

审计字段（created_by/updated_by）本质是"谁弄的"弱关联，导入的系统基础数据没有真实主人，硬绑外键反而别扭。去外键 + 约定 `0` 表"系统/导入数据"。

## 边界判断

`importer.user_id` 既用于审计字段（created_by，可去外键填 0），也用于业务归属字段（`ProductRecord.user_id`/`UserPlace.user_id` 等 `nullable=False` + 有外键 + 有 relationship），两者必须区分：

- **审计字段 created_by/updated_by**（AuditMixin）：去外键，约定填 0。grep 确认无任何 relationship 依赖（`foreign_keys.*created_by`/`back_populates.*created_by` 全无匹配），去外键零误伤。
- **Recipe.user_id**（[recipe.py:15](../backend/app/models/recipe.py#L15)）：菜谱作者业务字段，[:31](../backend/app/models/recipe.py#L31) 有 `user = relationship(...)` 依赖。**保留外键**，导入的公共菜谱改填 `None`（无个人作者，语义合理）。
- **invite_code.created_by**（[invite_code.py:27](../backend/app/models/invite_code.py#L27)）：有 `creator = relationship(...)` 挂载（[:34](../backend/app/models/invite_code.py#L34)），且邀请码是登录态创建（有真实 user_id）、不影响启动导入。**保留外键**，避免改造 relationship。
- **ProductRecord.user_id / UserPlace.user_id 等业务归属**：保留外键（多用户权限/价格归属/地点归属的业务核心）。export importer（用户上传导出包，登录态）走这些字段，不在启动流程，不崩。

## 修复

1. **[base_model.py](../backend/app/core/base_model.py)**：AuditMixin + BaseModel 的 created_by/updated_by 去掉 `ForeignKey("users.id")`，改 `Column(Integer, nullable=True)`，注释约定 `0=系统/导入数据`；清理未用的 `ForeignKey` import。
2. **[howtocook.py:207](../backend/app/services/importer/importers/howtocook.py#L207)**：Recipe 导入删 `user_id=self.user_id`（→ None，公共菜谱无作者，Recipe.user_id 外键保留 + nullable 合法）。
3. **[main.py:236,243](../backend/app/main.py#L236)**：启动导入 `user_id=1` → `user_id=0`（系统数据标记，喂给 importer 的 created_by/updated_by）。
4. **[main.py:270-271](../backend/app/main.py#L270)**：批量建商品 `created_by=1, updated_by=1` → `0, 0`。

importer 内部 `created_by=self.user_id`（howtocook.py:149-150）代码不动——main.py 传 0 后自然填 0。

## 验证

- `py_compile` base_model.py / howtocook.py / main.py 全过。
- PG 方言编译 `CreateTable`：
  ```
  --- Product ---
  created_by INTEGER,        ← 无 REFERENCES ✅
  updated_by INTEGER,        ← 无 REFERENCES ✅
  --- Recipe ---
  user_id INTEGER,
  created_by INTEGER,        ← 无 REFERENCES ✅
  updated_by INTEGER,        ← 无 REFERENCES ✅
  FOREIGN KEY(user_id) REFERENCES users (id),   ← 业务字段外键保留 ✅
  ```
- 审计字段去外键 + 业务字段（Recipe.user_id）外键保留，relationship 不伤。

## 未改动 / 边界保留

- `Recipe.user_id`、`ProductRecord.user_id`、`UserPlace.user_id`、`invite_code.created_by` 等带 relationship 或业务归属性质的字段外键**全部保留**。
- export importer（[export.py](../backend/app/services/importer/importers/export.py)）：登录态场景（用户上传导出包），有真实 user_id，不在启动流程，不动。
- **数据库迁移**：本次为约束（外键）变更，但无需提供三引擎 SQL 脚本——
  - 目标场景是 PG/MySQL **新建库**：`create_all` 按新模型直接建表（审计字段无外键），即生效。
  - SQLite **开发库**：`create_all` 不会 DROP 既有约束，旧外键还在；但 SQLite `foreign_keys` 默认 OFF 不校验，无影响。
  - 若存在**已建表的 PG/MySQL 既有库**需迁移（DROP 审计字段外键），可按需补脚本；当前检验支持场景（新库）不涉及。

## 影响

- 解锁 PG/MySQL 空库的启动导入（create_all + 初始数据导入全程不崩）。
- SQLite 开发库无影响（既有数据 created_by 仍是真实 user_id，去外键后仍合法；foreign_keys OFF）。
- 审计字段语义：`0` = 系统/导入数据，真实用户操作仍填其 user_id（无外键校验，均合法）。
- 运行时：uvicorn `--reload` 重启重跑 lifespan，PG 空库将从"崩在 products INSERT"推进到完整导入。
