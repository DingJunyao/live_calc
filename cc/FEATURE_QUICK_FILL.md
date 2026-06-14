# 功能：快速填写

日期：2026-06-14

## 需求

价格记录页面新增「快速填写」入口，进入独立页面，支持到一家超市后逐个批量记录商品价格：
- 选商家后自动列出该商家历史所有商品（按名称排序）
- 每行只填价格，数量/单位默认 1/斤，点击可改
- 可新增行搜索添加商品
- 保存时只保存填了价格的商品；近 1 小时内填过的商品按商家独立隐藏，未填的保留

页面移动端优先。

## 现状分析

- 价格记录页 `PricesView.vue` 是首页（`/` → `/prices`），含 app-bar（刷新按钮在 `#append` 槽）、列表、筛选、FAB 添加对话框。
- 后端已有可用接口：`GET /merchants`、`GET /merchants/{id}/product-prices`（返回商家各商品最新价格，含 `product_id`/`product_name`）、`GET /products/autocomplete`（商品搜索）、`POST /products`（创建价格记录，支持 `product_id` 或 `product_name`）。
- 无商家 store，商家列表各组件各自 `GET /merchants?limit=100` 加载。
- 消息提示各组件用内联 `v-snackbar` + ref 状态（`PricesView.vue` 即如此），无 `useSnackbar` composable。

## 实现

纯前端改动，后端无变更。

### 入口与路由

- `frontend/src/router/index.ts`：`/prices` 之后新增子路由 `prices/quick-fill`（name `quick-fill`，懒加载 `QuickFillView.vue`，title「快速填写」）。
- `frontend/src/views/prices/PricesView.vue`：`#append` 槽刷新按钮后加 `mdi-lightning-bolt` 图标按钮，点击 `$router.push('/prices/quick-fill')`。

### QuickFillView.vue（`frontend/src/views/prices/QuickFillView.vue`，新建）

- **导航栏**：左侧返回箭头（回 `/prices`）、标题、右侧 `mdi-check-all` 保存按钮（`:loading="saving"`）。
- **商家选择器**：`v-autocomplete`，`GET /merchants?limit=100` 加载；选中触发 `onMerchantChange`。
- **历史商品列表**：`onMerchantChange` 调 `GET /merchants/{id}/product-prices`（后端 SQL 已 `ORDER BY p.name ASC`），映射为 `FillRow[]`，**默认 price 空、quantity=1、unit='斤'**（不复用上次值，因为价格每次重填，数量/单位来源可能不同）。
- **每行布局**：商品名（只读）+ 价格输入框（`step=0.01`，placeholder `¥0.00`）+ `/` + 数量（默认显示文本，点击变 `v-text-field`）+ 单位（默认显示文本，点击变 `v-select`）。
- **新增商品区域**：`v-autocomplete`（`return-object`、`custom-filter="() => true"`、`#no-data` 创建提示），防抖 300ms 调 `GET /products/autocomplete`，结果过滤掉 `existingProductIds`（历史行 + 已选新增行的商品 ID）。
- **隐藏逻辑（sessionStorage）**：
  - key `quick-fill-hidden-{merchantId}`，value `[{productId, filledAt}]`。
  - `getHiddenItems` 读取时用 `Date.now() - filledAt < 3600000` 过滤（1 小时 TTL）。
  - `addHiddenItems` append 并写回，try/catch 静默降级（写满不报错）。
  - `visibleHistoryRows` computed 过滤隐藏 ID；`hiddenCount` 显示隐藏数；底部「── 近 1h 已填商品已隐藏（N 个）──」。
  - **按商家独立**（key 含 merchantId），**新增行不参与隐藏**（保存时只对 `!row.isNew` 的成功行写隐藏）。
- **保存（`saveAll`）**：收集 `price` 非空且 `>0` 的可见历史行 + 新增行；新增行填价但无商品则提示；逐条 `POST /products`（`record_type='purchase'`、`product_id` 或 `product_name`）；按成功/失败计数；成功的历史行 ID 写隐藏，成功的新增商品计入「已加入历史列表」提示；`successCount>0` 时重新 `onMerchantChange` 刷新；清空 `newRows`。snackbar 区分全成功/部分失败。
- **健壮性**：
  - `getRowProductId(row)` 兼容历史行的 `number` 和新增行的对象（`return-object` 返回 `{id,...}`），显式判 `null`。
  - `removeNewRow(index)` 同步重排 `newRowSuggestions` 和 `searchDebounceTimers`；搜索回调加 `newRows.value[index]` 存在性防御。
  - `onUnmounted` 清理所有 pending debounce timer。
- **样式**：移动端优先 `.fill-row*` flex 布局；价格/数量/单位/商品搜索的 `:deep(input)` 设 `font-size:16px` 防 iOS 聚焦缩放；编辑态文本点击区域加 padding 便于触控。
- **消息提示**：内联 `v-snackbar` + `showSnackbar(msg, color)`，与 `PricesView.vue` 同模式。

## 验证

- 前端 `npm run build` 通过（`QuickFillView` 约 8.8 kB）。
- 经 spec 合规审查 + 代码质量审查两轮，修复 record_type 缺失、return-object、timer 索引错位、内存泄漏、防重复选择、iOS 缩放、错误提示等问题。

## 设计与计划文档

- 设计：[docs/superpowers/specs/2026-06-14-quick-fill-design.md](../docs/superpowers/specs/2026-06-14-quick-fill-design.md)
- 计划：[docs/superpowers/plans/2026-06-14-quick-fill-plan.md](../docs/superpowers/plans/2026-06-14-quick-fill-plan.md)
