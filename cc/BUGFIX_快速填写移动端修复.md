# 快速填写页面移动端修复

日期：2026-06-16（第一轮），2026-06-16（第二轮）

## 问题与修复

### 1. 新增商品搜索下拉与 iOS Safari 地址栏重叠
- **根因**：`v-autocomplete` 下拉菜单默认渲染在输入框下方，在 iOS Safari 底部地址栏附近被遮挡。
- **修复**：给 `v-autocomplete` 添加 `:menu-props="{ maxHeight: 200, location: 'top' }"`，让下拉菜单向上展开。

### 2. 单位选择器只能选取斤/个且闪退
- **根因 A（闪退）**：单位编辑用 `v-if/v-else` 切换 `v-select` 和文本，`@blur="row.isEditingUnit = false"` 在 iOS Safari 上触发过快，Vuetify `v-select` 的菜单 DOM 尚未完成交互就被 `v-if` 销毁。
- **根因 B（单位少）**：`loadUnits` 解析 `(res).items || (res as any[])` 时，如果 `/units` 端点返回分页格式不匹配则 fallback 到 catch 只剩两个默认单位。
- **修复 A**：移除 `v-if/v-else` + `v-select` 方案，改用 `v-menu` + `v-list`（`location="bottom"` `origin="bottom"`），通过 `#activator` 的 `props` 绑定触发器，`@click` 直接设值。不再有 blur 竞态问题。
- **修复 B**：`loadUnits` 加 `is_common: true` 参数（常用单位 15 个），用 `Array.isArray(res)` 正确判断返回格式。
- **清理**：移除 `FillRow.isEditingUnit` 字段和 `v-select` 相关样式。

### 3. 批量保存缓慢
- **根因**：`saveAll` 用 `for` 循环串行 `await api.post`，逐条等待。
- **修复**：改为 `Promise.allSettled` 并发提交，限制并发数 `CONCURRENCY = 5` 分批执行；导航栏保存按钮旁加 `{{ current }}/{{ total }}` 进度显示。

## 第二轮修复（2026-06-16）

### 4. record_type 应为 price 而非 purchase
- **根因**：快速填写记录的是「看到的价格」而非「购买支出」，`record_type` 不该是 `'purchase'`。
- **修复**：`saveAll` 中 `record_type` 从 `'purchase'` 改为 `'price'`。

### 5. 单位列表仍然只有斤/个
- **根因**：`api.get('/units')`（无末尾斜杠）→ FastAPI 返回 **404**（非 307 重定向），走 catch 分支只剩两个默认单位。
- **验证**：`/api/v1/units` 直接 404；`/api/v1/units/` 正常返回 15 个常用单位。其他页面（UnitsView）一直用的是 `/units/`。
- **修复**：`loadUnits` 的请求路径改为 `/units/`（加末尾斜杠），与 UnitsView 一致。

### 6. 新增商品搜索下拉仍未紧贴输入框
- **根因**：`v-autocomplete` 嵌在 `v-list-item` 内，Vuetify 的 `v-list-item` 内部布局（padding/overflow）干扰了菜单的 activator 位置计算。
- **修复**：移除 `v-list` / `v-list-item` 包裹，历史商品行和新增商品行都改为普通 `div.fill-row-wrapper`，消除 Vuetify list 组件的布局干扰。菜单 `menu-props` 保持 `location: 'top'` + `eager: true`。

## 第三轮修复（2026-06-16）

### 7. 商品搜索改用 v-dialog 底部弹出
- **根因**：Vuetify 3 的 `v-menu` overlay 基于 `position: fixed`，在移动端 Safari/Chrome 里 `location="top"` 定位计算不准，菜单始终出现在 viewport 底部附近。尝试了 `v-autocomplete` 内置菜单、独立 `v-menu` + `activator="parent"` 均无效。
- **最终修复**：点击商品输入框时打开 `v-dialog`（`location="bottom"`，底部 sheet 风格），内含独立搜索框 + 候选列表。完全绕开 Vuetify overlay 的定位问题。
  - 文本框 `readonly` + `@click="openProductDialog(i)"` 触发弹窗
  - 弹窗有搜索框（`autofocus`）、候选 `v-list`、loading 指示器、「确定」按钮
  - 选商品 → `selectDialogProduct`；不选只输入名称 → 点「确定」`confirmDialogProduct` 创建新商品
  - 清理了不再需要的 `onNewRowSearch`、`selectNewRowProduct`、`newRowSuggestions`、`searchDebounceTimers` 等

### 8. 历史商品按原料分类分组显示
- **后端**：`GET /merchants/{id}/product-prices` 的 SQL 增加 `LEFT JOIN ingredient_categories ic ON ic.id = i.category_id`，返回 `category_id` / `category_display_name` / `category_sort_order`。`ORDER BY COALESCE(ic.sort_order, 999999) ASC, p.name ASC`（兼容 SQLite/MySQL/PostgreSQL）。
- **前端**：`FillRow` 增加 `categoryId` / `categoryName` 字段；`groupedHistoryRows` computed 按 `categoryName` 分组（保持后端返回的分类排序，组内按拼音排序）；模板用 `v-for` 遍历分组，每组显示分类名标题。

## 第四轮修复（2026-06-16）

### 9. v-autocomplete 下拉列表偏移（最终方案）
- **根因**：Vuetify 3 的 `v-autocomplete` 默认将下拉菜单通过 Teleport 挂载到 `body`，使用 `position: fixed` 定位。在 iOS Safari 中，`fixed` 定位基于 layout viewport 而非 visual viewport，当地址栏展开/收缩时产生偏移。同时 `v-list-item` 内部的 `overflow: hidden` 会裁剪 attach 模式下的下拉列表。
- **最终修复**：
  - 恢复原始 `v-autocomplete`（移除之前所有的 `menu-props` / `v-menu` / `v-dialog` 改动）
  - 添加 `attach` 属性：让下拉列表挂载到组件自身 DOM 位置，不再 teleport 到 body，彻底规避 iOS Safari 的 `position: fixed` viewport 偏移问题
  - CSS 覆盖：`.fill-list :deep(.v-list-item) { overflow: visible; }` 和 `.fill-list :deep(.v-list-item__content) { overflow: visible; }`，解除 Vuetify list 组件的 overflow 裁剪

## 影响范围

- 前端：`frontend/src/views/prices/QuickFillView.vue`
- 后端：`backend/app/api/merchants.py`（product-prices SQL 增加分类 JOIN 和返回字段）
- 构建通过
