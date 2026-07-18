# 移动端详情页导航栏溢出菜单

## 问题
移动端（窄屏）各详情页顶部 `v-app-bar` 右侧操作按钮过多，把标题挤成省略号、看不出是什么页面。按钮无任何响应式显隐控制，所有尺寸下平铺。

## 根因
四详情页（菜谱/原料/商品/商家）`<template #append>` 内的操作按钮（2~4 个）全用 `<v-btn>` 平铺，无 `v-if`/display 断点控制。菜谱详情最严重（发布+删除+分析+刷新 4 个，删除还有可删/不可删两态），窄屏标题 `text-truncate` 被挤到只剩一两个字。

## 方案
桌面端（`isDesktop = mdAndUp`，≥960px）按钮原样平铺不动；移动端（`!isDesktop`）右侧按钮全部收进 `v-menu` 三点溢出菜单（`mdi-dots-vertical` + `v-list`），点击展开。每页内联（四页按钮集合差异大，不抽公共组件，靠写法一致性收敛）。

### 关键决策（用户拍板）
- **刷新也收进菜单**：原料/商品/商家详情页只有 2 按钮（操作+刷新），若刷新留外面则移动端变「刷新+三点」仍 2 个按钮、标题没省到。全收进才能真正瘦成单个三点按钮。
- **loading 放三点按钮（activator）上**：`v-list-item` 不支持 loading，把发布/删除/刷新的异步反馈挪到 `<v-btn :loading="anyLoading">`。任一进行时三点图标变转圈，不用打开菜单就知道在忙；`v-btn` loading 自动禁用也防操作中途重复点菜单。

### 沿用既有机制
- `isDesktop`：四页都已 `const { isDesktop, toggleSidebar } = useMobileDrawerControl()`（[useMobileDrawer.ts](frontend/src/composables/useMobileDrawer.ts)，`isDesktop = mdAndUp`），直接用，不引新依赖、不另设断点。
- `v-menu` 写法参考 [QuickFillView.vue:82](frontend/src/views/prices/QuickFillView.vue#L82)（项目既存 v-menu）。

## 涉及文件（4 个，模式统一）
- [RecipeDetail.vue](frontend/src/views/recipes/RecipeDetail.vue)：`<template #append>` 加 `v-if="isDesktop"` 包原按钮组 + `v-else` 三点菜单（发布/删除两态/分析/刷新）；script 加 `const anyLoading = computed(() => publishing.value || loading.value || deleting.value)`（排在 publishing 声明后防 TDZ）。
- [IngredientDetail.vue](frontend/src/views/ingredients/IngredientDetail.vue) / [ProductDetail.vue](frontend/src/views/products/ProductDetail.vue)：原 2 按钮（记价 `mdi-tag-plus` + 刷新）→ 桌面原样 + 移动三点（记录价格/刷新），`:loading="loading"`。
- [MerchantDetail.vue](frontend/src/views/merchants/MerchantDetail.vue)：原 2 按钮（编辑 `mdi-pencil` + 刷新）→ 桌面原样 + 移动三点（编辑商家/刷新）。

### RecipeDetail 删除两态合并
桌面端原是互斥两分支：可删 `mdi-delete`（`v-if="canManage || !isPublished"`）/ 不可删 `mdi-delete-off-outline`+tooltip（`v-else`）。移动端菜单合并成一个「删除菜谱」位：可删 `<v-list-item ... @click="showDeleteDialog = true">`、不可删 `v-else ... subtitle="已发布菜谱不可删除，请联系管理员" disabled`，语义与桌面 tooltip 对齐。发布项 `v-if="canPublish"`、`:disabled="!recipe"` 迁到 `v-list-item`；`base-color="success"/"error"` 保留按钮配色。

## 不动
- [RecipeAnalysisView.vue](frontend/src/views/recipes/RecipeAnalysisView.vue)：仅 1 个刷新按钮，不触发收纳条件。

## 统一改造模板
```vue
<template #append>
  <!-- 桌面端：按钮平铺 -->
  <template v-if="isDesktop">
    <!-- ...原 v-btn 原样... -->
  </template>
  <!-- 移动端：三点溢出菜单 -->
  <v-menu v-else :close-on-content-click="true" location="bottom end">
    <template #activator="{ props: menuProps }">
      <v-btn icon="mdi-dots-vertical" variant="text" v-bind="menuProps" :loading="anyLoading" />
    </template>
    <v-list density="compact" nav>
      <v-list-item prepend-icon="..." title="..." @click="..." />
    </v-list>
  </v-menu>
</template>
```

## 验证
- `npm run build` 通过（15.55s，✓ built），四页产物均在（RecipeDetail 52.96 kB / ProductDetail 59.15 kB / IngredientDetail 92.10 kB / MerchantDetail 13.85 kB）。chunk 大小警告为既存（nutritionLabels/RecipeAnalysisView/index），与本次无关。
- chrome-devtools MCP 连不上 Edge（9222 调试端口未开），移动端形态待开发者手动核对：缩窗 <960px 看四页右侧是否单个三点按钮、点开菜单各项可用、刷新时三点转圈；桌面端 ≥960px 按钮原样平铺。

## 教训
- 「保留常用按钮在外面」未必更优——当目标就是减少按钮数时，留一个等于白改。先算清每页按钮数 vs 收纳目标，再定保留策略（本例：2 按钮页留刷新=仍 2 按钮，收纳失效）。
- `v-list-item` 不支持 loading，activator 承载 loading 是 v-menu 场景的通用解法。
- 无表结构变更，纯前端。

## 续：商家管理列表项溢出菜单（所有端，非仅移动端）
[MerchantsView.vue](frontend/src/views/data/MerchantsView.vue) 列表项 `<template #append>` 原 4 个小按钮（收藏 `mdi-heart/outline`、定位 `mdi-crosshairs-gps`、编辑 `mdi-pencil`、删除 `mdi-delete`）平铺，桌面端也挤。用户要求所有端都收（非仅移动端），且定位（高频、要看坐标禁用态）留外面。改造：定位 v-btn 留列表项，收藏/编辑/删除 进 v-menu 三点菜单（`mdi-dots-vertical` activator，`size=small` 对齐原按钮）。菜单项 `@click` 不需 `.stop`——v-menu 内容 teleport 到 overlay，不冒泡到外层 v-list-item 触发跳详情（原 v-btn 用 `.stop` 是因它本身在 list-item DOM 内）；收藏项 `:base-color` 已收藏 error，靠 prepend-icon heart/outline + title 表态。所有端统一，不包 `v-if isDesktop`。build 通过（13.03s）。
