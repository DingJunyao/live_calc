# DEBUG：Edge PWA 点击/刷新唤起外部浏览器（定性为 Edge 行为）

## 症状
Edge 安装的 PWA 里点侧边菜单或刷新，会把焦点甩给 Edge 主窗口——没有 Edge 窗口时新建一个空白窗口（about:blank、无标签页），已有 Edge 窗口时激活到前台但不打开任何页面。应用内 SPA 跳转本身正常（URL/内容正确改变）。

## 排查（四连排除 + 二分 + 运行时 hook）

1. **grep src**：无 `window.open` / `target="_blank"` / `location=`（除 [client.ts](frontend/src/api/client.ts) 401 跳登录，无关）。
2. **dist manifest**：`scope:'/'`、`start_url:'/'`、`id:'/'` 全正常，排除 scope 问题。
3. **二分**：注释 `display_override`(WCO) + `protocol_handlers`，重装仍唤起 → 排除。
4. **echarts openLink**：dist 的 `window.open` 在 nutritionLabels/RecipeAnalysisView chunk，是 echarts `openLink`（format.js 的 `Tc` 函数），但项目 graphic（[CostProportionChart](frontend/src/components/recipes/CostProportionChart.vue)、[NutritionSourceGrid](frontend/src/components/recipes/NutritionSourceGrid.vue)）都无 `link` 配置 → 库死代码不调用，排除。
5. **Console hook `window.open`**：点击无 `[WO]` → 非应用主动调。
6. **bubble 阶段 hook**：`<a>` 点击 `defaultPrevented=true` → 拦截器/Router 正常 preventDefault，非漏拦。（注意：capture 阶段读 `defaultPrevented` 必为 false，无信息量——这是排查中踩过的坑。）
7. **关键线索**：刷新也唤起 → 非点击/`<a>` 特有，是加载/导航相关机制。
8. **Chrome 对照**：用 Chrome 装 PWA 完全正常 → 实锤 Edge PWA standalone 窗口管理特性/bug。

## 结论
**Edge PWA 特有行为，非应用代码问题。** 代码层面改不动。绕法：edge://apps 里该应用的设置，或忽略——部署后 Chrome/其他浏览器正常。

## 附：main.ts 全局 click 拦截器
排查中在 [main.ts](frontend/src/main.ts) 加了通用兜底（站内 `<a href="/...">` 点击 `preventDefault` + `router.push`，覆盖 v-list-item / v-btn / router-link 所有渲染成 `<a>` 的组件）。Chrome 也受益、无害，保留。

## 教训
PWA 点链接开外部浏览器 → **先 Chrome 对照**判断是不是浏览器特有行为，再查应用代码。本次前期假设（preventDefault 缺失 / WCO / protocol / echarts openLink）全部落空，最终 Chrome 对照一击命中。systematic-debugging 的"隔离变量"（换浏览器）比静态 grep 更快定位这类环境特有行为。
