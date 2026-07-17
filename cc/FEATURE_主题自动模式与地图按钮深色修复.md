# 主题自动模式 + 地图切换按钮深色修复

## 需求
1. 浅色/深色模式优化：新增「自动」模式，根据系统/浏览器的 `prefers-color-scheme` 自动决定明暗。
2. 商家管理地图切换按钮组（高德/百度/腾讯/天地图/OSM），深色模式下未选中按钮文字颜色太浅。

## 现状摸底
### 主题
- `composables/useTheme.ts` 早已写好三态（light/dark/system）+ localStorage 持久化 + matchMedia 监听 + 应用到 Vuetify 的完整逻辑，但**是死代码，全项目零引用**（grep `useThemeToggle` 无 import）。
- 实际在跑的是 3 处各写各的 inline 逻辑（`useTheme()` from vuetify + 本地 `isDark`/`toggleTheme`，纯二态、不持久化、不监听系统、刷新回退浅色）：
  - `components/layout/AppLayout.vue`（桌面侧边栏 L37-41 + 移动抽屉 L95-99，两处 UI）
  - `components/layout/DesktopNav.vue`（**遗留死代码**，grep 全 src 零引用）
  - `views/profile/ProfileView.vue`（个人中心设置项 L67-78）
- `index.html` 无 head bootstrap → 刷新必闪白、回退 `defaultTheme='light'`。

### 地图按钮
- 商家管理页（`views/data/MerchantsView.vue`）本身无切换 UI，地图整体委托给子组件 `components/map/MerchantMapView.vue`。
- 桌面端切换按钮组（template L23-34）：选中 `color=primary variant=elevated`（绿底白字，正常）；未选中 `color=default variant=text`（文字跟随 `on-surface`）。
- 病灶：scoped CSS `.desktop-layer-selector { background: white }`（L1045）硬编码白底 → 深色下未选中按钮的浅灰文字（on-surface `#E3E3DB`）落在白底上几乎看不清。
- 移动端用 `v-select variant=solo`（自带 surface 底），不受影响。

## 方案

### 任务一：主题三态（用户拍板：ProfileView 原地按钮组 + 侧边栏保留快切）
- **复活 useTheme.ts 并单例化**：响应式 state（`themeMode`/`prefersDark`）、matchMedia 监听器、`actualTheme` computed、`toggleTheme`/`setThemeMode` 全部提到模块顶层，只初始化一次；`useThemeToggle()` 仅负责把 `actualTheme` 绑定到 Vuetify（`vuetifyBound` 标志位确保只绑定一次）。新增导出 `isDark`、`prefersDark`。多处调用零副作用（监听器不累积）。
- **index.html 防 FOUC**：head 加内联 `<style>`（`html[data-theme=light|dark] body` 背景色）+ 内联 `<script>` 读 `localStorage('theme-mode')` + `matchMedia('(prefers-color-scheme: dark)')` 解析初始主题，写 `window.__INITIAL_THEME__` + `document.documentElement.data-theme`。解析逻辑与 useTheme.ts 的 actualTheme 保持一致。
- **vuetify.ts**：`defaultTheme` 从写死 `'light'` 改读 `window.__INITIAL_THEME__`（兜底 `'light'`）。
- **useTheme.ts 运行时同步 data-theme**：`actualTheme` watch 里 `setAttribute('data-theme', newTheme)`，驱动 body 防闪背景跟随运行时切换（首屏由 bootstrap 设、运行时由 useTheme 维护）。
- **AppLayout.vue**：删 inline `useTheme`/`isDark` computed/`toggleTheme`，接入 `useThemeToggle`（取 `themeMode`/`toggleTheme`）。侧边栏主题切换改为三态**图标按钮组**（v-btn-toggle 仅图标，对齐个人中心外观主题、w-100 三等分）：桌面展开模式与移动抽屉直接显示按钮组，桌面 rail（收起）模式退化为单图标 v-list-item（`themeIcon` + `toggleTheme` 单击三态循环，避免窄条挤三个按钮）。`toggleTheme` 在 useTheme.ts 实现为 浅色→深色→自动→浅色 循环；`themeTitle` 文案 computed 移除（按钮组仅图标、rail 单图标无文字）。
- **ProfileView.vue**：「主题切换」单项改成原地三态：`v-list-item` 内放「外观主题」标题行 + 右侧 `themeModeLabel` + 下方 `v-btn-toggle`（浅色/深色/自动，带图标，`w-100` 三等分铺满，`mandatory`+`color=primary`+`divided`）；`v-model` 直接绑 `useThemeToggle` 返回的 `themeMode` 单例 ref（写入即触发持久化 watch + Vuetify 应用）。删 inline useTheme/isDark/toggleTheme，加 `themeModeLabel` computed。

### 任务二：地图按钮（一行收束）
- `MerchantMapView.vue` L1045 `.desktop-layer-selector` 的 `background: white` → `rgb(var(--v-theme-surface))`。底色跟随主题（浅色 `#FDFCF8` 米白 / 深色 `#1B1C18`），未选中按钮的 on-surface 文字深浅色下均清晰；与该文件 L1074 `.map-loading-overlay` 既有的 surface 写法对齐。选中按钮绿底本就正常，不动。

## 改动文件
- `frontend/src/composables/useTheme.ts`（重写为单例）
- `frontend/index.html`（head 加防闪 style+script）
- `frontend/src/plugins/vuetify.ts`（defaultTheme 读 `__INITIAL_THEME__`）
- `frontend/src/components/layout/AppLayout.vue`（接入 useThemeToggle）
- `frontend/src/views/profile/ProfileView.vue`（三态按钮组 + 接入 useThemeToggle）
- `frontend/src/components/map/MerchantMapView.vue`（地图按钮背景跟随主题）

## 验证
- `npm run build` 通过（28.38s），无 TS/编译错误，仅既有 chunk size warning（与本次无关）。ProfileView chunk 30.94 kB、MerchantMapView 15.35 kB 均正常。
- 运行时行为（逻辑走查）：
  - 首次访问无 localStorage → 默认 `system` → 跟随系统偏好；选择浅色/深色 → 持久化到 localStorage；刷新 → bootstrap 先按 localStorage 调对底色（不闪白），Vuetify 实例 defaultTheme 同步，`useThemeToggle` 的 immediate watch 再对齐一次。
  - system 模式下系统切换明暗 → matchMedia `change` 事件实时跟随。
  - 侧边栏主题切换：桌面展开 / 移动抽屉为三图标按钮组（浅色/深色/自动，高亮当前档）；桌面 rail 收起模式为单图标，单击三态循环（`toggleTheme`）。
  - 商家地图切换按钮：深色模式下未选中按钮文字（on-surface 浅灰）落在 surface 深底上清晰可见。

## 遗留 / 待确认
- `components/layout/DesktopNav.vue`（遗留死代码，含旧 inline 主题逻辑）已删除（用户确认；删除前全 src grep 零引用、未被 import 不进 bundle，git 可恢复）。
- 首屏 bootstrap 与 useTheme.ts 的「mode→dark 解析」逻辑各维护一份（index.html 不能 import 模块，不可避免），后续调整解析规则时两处须同步。
- `v-btn-toggle` 在极窄屏（<320px）三个「图标+文字」按钮可能略挤，必要时可只留图标或换下拉。
