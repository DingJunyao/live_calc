# 地图两个下拉移动端样式统一

## 问题
[MerchantMapView.vue](frontend/src/components/map/MerchantMapView.vue) 移动端「选择地图」和「选择常用地点」两个 v-select 紧挨着却样式不一致：地图下拉被 CSS 缩小（80px 宽 / 0.7rem 字号 / 压扁内边距与高度），地点下拉用默认大小，视觉割裂。

## 根因
- 地图下拉（原 class `mobile-layer-selector`）有专门移动端 media query CSS 缩小；地点下拉**没有任何移动端适配**。
- 附带 bug：地图下拉内联 `style="max-width:120px"` 优先级高于 class CSS 的 80px，那条 80px 一直没生效（实际显示 120px）。

## 方案
抽公共 class `map-control-select`，两个 v-select 共用同一套样式：
- 桌面默认 `.map-control-select { max-width: 150px }`（桌面端地图走按钮组不渲染下拉，仅地点下拉受此约束）。
- 移动端 media query 统一：`.map-control-select { max-width: 80px; font-size: 0.7rem }` + `:deep(.map-control-select .v-field__input) { padding: 4px 8px; min-height: 28px; font-size: 0.7rem }`。
- 去掉两个 v-select 的内联宽度（地图下拉删 `style="max-width:120px"`、地点下拉删 `:style="{ maxWidth: isDesktop ? '150px':'110px' }"`），宽度统一交 CSS 控制不再打架。
- 删冗余的 `:deep(.mobile-layer-selector)` 重复块与 `.mobile-layer-selector { display:none/block }`（v-if/v-else-if 已互斥渲染控制显隐，CSS display 多余）。

## 涉及文件
- [MerchantMapView.vue](frontend/src/components/map/MerchantMapView.vue)：模板 2 处（两个 v-select 的 class 换成 `map-control-select` + 去内联宽度）+ CSS 3 处（桌面默认、移动端 media query、`:deep(.v-field__input)`）。

## 验证
`npm run build` 通过（13.14s）。chrome-devtools 连不上 Edge 9222，移动端两个下拉并排等宽等高待开发者手动核对。无表结构变更。

## 教训
- 内联 style 优先级高于 class CSS：想用 class 控宽度就别留内联宽度，否则 CSS 静默失效（本例 80px 被 120px 内联盖掉）。
- 相邻同类控件（一组下拉/按钮）应共用 class 统一响应式样式，避免逐个手写致漂移。

## 续：宽度按内容差异化（修正「全部商家」截断）
首版统一把两个下拉移动端 max-width 都设 80px，但地点下拉选项文案更长（「全部商家」4 字、用户地点名可能更长），80px 装不下致显示不全。修正：**风格（字号/内边距/高度）仍统一，宽度按内容差异化**——地点下拉加修饰 class `place-select`，移动端 `.map-control-select.place-select { max-width: 120px }`（双 class 选择器优先级高于单 class，覆盖 80px）；地图下拉仍 80px（选项是「高德」「百度」等短名够用）。build 通过（12.82s）。

教训补充：「样式统一」指字号/高度/内边距/配色等视觉风格一致，**宽度应按各自内容留余**，强行等宽会截断长文案。上一条「共用 class 统一响应式样式」要用修饰 class 做内容差异化覆盖，不是一刀切等宽。
