# 商家列表筛选样式微调

## 问题
上一轮 [[FEATURE_禁用地图总开关]] 把商家列表改成「地图启用=左列表+右地图 / 地图禁用=卡片网格(桌面)·列表(移动)」后，地图禁用态桌面端筛选项有两处体验问题：
1. 桌面端出现「清除筛选」按钮，用户觉得多余（筛选项就 3 个，单独取消即可，不需要批量清除）
2. 搜索框与筛选项之间间距太窄（`ga-2`=8px），视觉上挤

## 根因
- FilterBar 是公共组件（[FilterBar.vue](frontend/src/components/common/FilterBar.vue)），被 5 个页面共用（Merchants/Prices/Recipes/Products/Ingredients）。桌面 inline 模式末尾有通用「清除筛选」按钮（[:332-344](frontend/src/components/common/FilterBar.vue#L332-L344)），有激活筛选就显示——其他 4 个页面仍需要它，不能直接删
- 地图禁用态搜索+筛选外层 `ga-2`（[MerchantsView.vue:197](frontend/src/views/data/MerchantsView.vue#L197)）

## 修复
KISS + 开放封闭，给公共组件加开关而非硬删：
1. **FilterBar.vue** 加可选 prop `hideClearButton?: boolean`（默认 `false`，向后兼容，其他 4 页面零影响），桌面 inline「清除筛选」按钮 `v-if` 由 `hasActiveFilters` → `hasActiveFilters && !hideClearButton`。移动端 modal 内的「清除」按钮是另一套（`v-if="mobile"` 分支内），不受此 prop 影响
2. **MerchantsView.vue** 地图禁用态（B 分支）的 FilterBar 传 `:hide-clear-button="isDesktop"`（桌面隐藏、移动端 modal 清除按钮保留），外层 `ga-2` → `ga-3`（12px，留呼吸空间）

## 关键点
- `hideClearButton` 只作用于桌面 inline 清除按钮。因为移动端走 `v-if="mobile"` 分支根本不渲染桌面 inline 部分，prop 对移动端天然无效，所以传 `isDesktop`（桌面时 true）还是常量 `true` 运行时效果一致——选 `isDesktop` 是为语义贴合「桌面端不需要」的用户描述，可读性更好
- 商家列表地图启用态左面板（350px 窄）写死 `mobile` 走 modal 模式，不受本次改动影响

## 验证
- 前端 `npm run build` 通过（27.16s，precache 128 entries 不变）
- 无表结构变更，纯前端 2 文件改动
- 其他 4 个使用 FilterBar 的页面因 prop 默认 false，行为不变

## 续：页宽统一
紧接着发现地图禁用态商家管理页比其他列表页宽。根因：所有列表页（Prices/Products/Recipes/Ingredients/QuickFill）外层都用 `<v-container fluid class="list-grid-container">`，靠 [responsive.css:54](frontend/src/assets/css/responsive.css#L54) 的 `max-width:1600px; margin:0 auto` 约束页宽；商家管理 B 分支用的是 `<div class="w-100">` 无 max-width 约束，>1600px 宽屏一路撑满。地图启用态（A 分支左列表+右地图）要铺满屏幕不动，只统一禁用态：B 分支 div 加 `list-grid-container` 类 → `<div class="w-100 list-grid-container">`。`w-100`（width:100%!important）撑满 + `max-width:1600px` 限制 + `margin:0 auto` 在 flex 容器 main-content 里居中（flex 子项 margin auto 吸收剩余空间）；移动端屏幕窄 max-width 不触发正常撑满。padding 仍由 main-content 的 `padding:1rem` 提供，与其他页面 `pa-4` 一致。一行 class 改动，build 通过（15.12s，precache 128 entries 不变）。

## 教训
公共组件的某个细节在单一场景不合适时，加可选开关（默认保持原行为）比硬删更安全，符合开放封闭原则；gap 类间距问题用 Vuetify 的 `ga-N` 工具类比手写 CSS 优雅；新页面/新分支的容器要复用项目已有的全局容器类（`list-grid-container`）统一页宽，别用裸 `w-100` 撑满，否则宽屏上会和其他页面对不齐。
