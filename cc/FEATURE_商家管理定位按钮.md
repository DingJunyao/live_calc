# 商家管理列表「定位」按钮

## 背景

商家管理页（`MerchantsView`）左侧列表每项只有「编辑」「删除」按钮，点击列表项整体跳详情页。右侧虽常驻地图（`MerchantMapView`），但缺少「在地图上定位某个商家」的直接入口。

需求：列表每项加一个定位按钮，点击后地图居中显示该商家，并加特殊标记（与商家详情页一致）。

## 关键发现（为何改动极小）

`MerchantMapView` 早就内建「选中商家」机制：

- 接收 `selectedMerchant` prop
- `watch(() => props.selectedMerchant)` 一变化即：
  - 调 `updateMerchantsMarkers()` 重绘全部标记（选中项套 `selected` 红色样式，SDK 引擎用 `#d32f2f`）
  - `currentEngine.setCenter()` + `setZoom(15)` 居中

商家详情页 `MerchantDetail.vue` 的「特殊标记」就是把商家同时传 `merchants` 和 `selected-merchant` 复用这套机制。而 `MerchantsView` 本就传了 `:selected-merchant="selectedMerchant"`，只是从无人设置 `selectedMerchant`（原仅在 save/delete 里维护）。

→ 结论：地图组件零改动，只需在列表补「谁来设 selectedMerchant」这一环。

## 实现（仅改 `frontend/src/views/data/MerchantsView.vue`）

1. **模板**：列表项 `#append` 按钮组最前加定位按钮
   - icon `mdi-crosshairs-gps`，color `secondary`（与详情页「位置」卡片配色区分于编辑 primary / 删除 error）
   - `@click.stop="locateMerchant(item)"` 阻止冒泡，避免触发列表项整体的跳详情
   - `:disabled="!isValidCoordinate(item.latitude, item.longitude)"`，无坐标时禁用，title 提示「未设置位置」

2. **模板**：右侧地图面板 `<div class="right-panel" ref="rightPanelRef">`（移动端滚动用）

3. **script**：
   - `import` 补 `nextTick`
   - 新增 `rightPanelRef = ref<HTMLElement | null>(null)`
   - 新增 `isValidCoordinate(lat, lng)`：判定与 `MerchantMapView` 完全一致（number、非 NaN、非 0）
   - 新增 `locateMerchant(item)`：有坐标才设 `selectedMerchant.value = item`；移动端 `nextTick` 后 `rightPanelRef.scrollIntoView({ behavior: 'smooth', block: 'center' })`（`center` 避开 fixed app-bar 遮挡）

## 行为

- 桌面端：点定位 → 右侧地图该商家居中、标记变红（与详情页视觉一致）
- 移动端：点定位 → 滚动到下方地图 + 同上居中变红
- 无坐标商家：按钮禁用，不可点

## 设计取舍

- 不引入全局 snackbar 提示无坐标，改用按钮 `disabled` + title —— 更克制（KISS），少一个依赖
- `isValidCoordinate` 本地内联而非抽共享工具 —— 项目现状就是 `MapPicker`/`MerchantMapView` 各自重复一份，不为此小功能引入新抽象（YAGNI）
- 不做「再点一次取消选中」toggle —— 当前需求只要定位，保持简单

## 验证

- `npm run build` 通过（10.13s，无类型错误）
