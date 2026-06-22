# 邀请码过期时间无法指定 · BUGFIX

## 现象
后台「邀请码管理」→「创建邀请码」对话框里，「过期时间」一栏空白、没有日期控件、点不动，无法指定过期时间。编辑对话框同理。

## 根因（三处叠加）

### 1. 前端组件未注册 + 组件选型错误
- 该栏用的是 `<v-date-input>`。Vuetify 3.12.4 里 `VDateInput` 属 **labs 组件**（物理位于 `vuetify/lib/labs/VDateInput/`），与稳定版 `vuetify/components` 是 [vuetify package.json](../frontend/node_modules/vuetify/package.json) exports 里两套独立导出（`./components` vs `./labs/components`）。
- 项目 [vuetify.ts](../frontend/src/plugins/vuetify.ts) 只 `import * as components from 'vuetify/components'`，从未注册 labs；[vite.config.ts](../frontend/vite.config.ts) 里 `vite-plugin-vuetify` 的 `autoImport: true` 只注入样式、不碰组件 JS 注册。
- 结果：运行时 `Failed to resolve component: v-date-input`，该栏渲染成空壳。
- 即便注册成功，`v-date-input` 只到「天」，承载不了「时间点（时分）」语义。
- `v-date-input` 全项目仅此一处用，故 bug 只暴露在邀请码页。

### 2. 后端 is_expired 的 naive/aware TypeError（修好前端会触发）
- `expires_at` 是 `DateTime(timezone=True)`，但 SQLite 方言读回的是 **naive datetime**（无 tzinfo）——参 products 模块 [products.py:459-467](../backend/app/api/products.py#L459) 也得手动 `datetime.fromtimestamp(ts)` 把 aware 转 naive 才能比较，印证了读回是 naive。
- 旧 `is_expired` 写 `self.expires_at < datetime.now(timezone.utc)`，naive vs aware 直接抛 `TypeError: can't compare offset-naive and offset-aware datetimes`。
- 此前没崩，仅因前端一直没法填 `expires_at`、该列全 NULL、`is_expired` 在首项短路。**修好前端即触发后端崩**，必须同修。

### 3. 序列化抹掉时区
- [_serialize_invite_code](../backend/app/api/invite_codes.py) 用 `strftime('%Y-%m-%dT%H:%M:%S')` 输出无时区串。
- 前端 [formatToLocalDateTimeShort](../frontend/src/utils/timezone.ts)（注释明确「需带时区信息」）靠 `new Date()` 解析；无 `Z` 串被当本地时间，列表「创建时间/过期时间」列本来就差一个时区。

## 修复（「后端统一 UTC、前端按本地时区」闭环）

### 前端 [InviteCodesView.vue](../frontend/src/views/admin/InviteCodesView.vue)
- 创建/编辑对话框 `v-date-input` → `<v-text-field type="datetime-local">`（复用 [PricesView](../frontend/src/views/prices/PricesView.vue#L273) 既有模式）。
- 状态 `expiresAt: Date|null` → `string|null`（datetime-local 字符串）。
- 提交：`new Date(localStr).toISOString()`（本地 → UTC，带 `Z`）。
- 编辑回填：新增局部 `toDatetimeLocalValue(isoStr)`（照 PricesView 写法），UTC ISO → 本地 `YYYY-MM-DDTHH:mm`。
- 创建对话框 `:min="getLocalDateTimeString()"`（datetime-local 的 min 要本地格式，非 toISOString）。

### 后端模型 [invite_code.py](../backend/app/models/invite_code.py)
- 新增模块级 `ensure_utc(dt)`：naive 视作 UTC、aware 转 UTC。对 SQLite/PG/MySQL 三库读法都鲁棒。
- `is_expired` 改 `ensure_utc(self.expires_at) < now(utc)`，防 TypeError。

### 后端序列化 [invite_codes.py](../backend/app/api/invite_codes.py)
- `_serialize_invite_code` 的 `expires_at`/`created_at` 改 `ensure_utc(dt).isoformat()`，输出带 `+00:00`。

### 测试 [test_invite_code.py](../backend/tests/models/test_invite_code.py)
- 10 例：`ensure_utc` 三态（naive/aware/已UTC）、`is_expired` naive/aware/None（核心防 TypeError）、序列化带时区、None、生成码形状。

## 不在范围
- `update_invite_code` 的 `if expires_at is not None` 无法清空过期时间（设回永不过期）——既有 bug，未处理。
- prices 的 `recorded_at` 走另一套 naive 本地模式，不重构。
- 无数据库迁移：`expires_at` 列在 [initial 迁移:92](../backend/alembic/versions/20260305_1927_c2c83a3a2304_initial_database_schema_with_all_models.py#L92) 就有，无历史数据（前端一直填不了），无需 SQL 脚本。

## 验证
- 后端：`pytest tests/models/test_invite_code.py` → 10 passed（用根 `.venv` 在 backend 目录跑：`& d:\code\live_calc\.venv\Scripts\python.exe -m pytest ...`；勿用 `uv run --directory backend`，会在 backend 误建空 venv）。
- 前端：`npm run build` 通过（InviteCodesView chunk 正常生成）。
- UI 闭环：需管理员账号（当前浏览器登录为普通用户 `qwertyu111`，`adminOnly` 路由不可达）。待管理员实测：创建带过期时间 → 列表按本地时间显示（带时分）→ 编辑回填正确 → 用该码注册验证过期校验（过期前成功/过期后拒）。

## 关键教训
- Vuetify labs 组件（`v-date-input` 等）必须显式注册 `vuetify/labs/components`，否则静默失败（Vue 仅 console warn，页面空白）。
- SQLite 的 `DateTime(timezone=True)` 读回 naive，跨库时区逻辑要防御式 `ensure_utc`，别直接和 aware 比。
- 「时间点」需求别用只到天的 date 组件，直接 `datetime-local`。
