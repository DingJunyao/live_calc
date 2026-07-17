# 前端 PWA 适配 — 设计文档

> 日期：2026-07-17
> 状态：待实现

## 背景

前端技术栈为 Vue 3 + Vite 5 + TypeScript + Vuetify 3，路由用 `createWebHistory()`（HTML5 history 模式），生产由 nginx 部署，已有 SPA 兜底（`try_files $uri $uri/ /index.html`）与静态资源长缓存规则。

PWA 现状为**一片空白**（均已代码层确认）：

- 无 `manifest.webmanifest`、无 service worker、无 `vite-plugin-pwa`
- [public/](frontend/public/) 目录为空
- [index.html](frontend/index.html#L5) 引用的 `/vite.svg` 文件实际不存在
- 项目无自己的 logo / 图标资源（仅 leaflet 库自带的 svg）
- 全库 grep `service.?worker` / `workbox` / `vite-plugin-pwa` / `PWA` 零业务匹配（仅菜谱导入页文案提及 `manifest.json` 是数据导出格式，与 PWA 无关）

用户需求：以**最小集**为目标——让 app 可安装到桌面/主屏（installable），联网使用即可。边界为**纯前端资产 + nginx 必需 header + 部署文档**，不涉及 HTTPS 证书/TLS 配置（由开发者部署时另行处理，文档给指引）。

## 目标

- **可安装**：满足 PWA installable 三要件（HTTPS / localhost、manifest 含 icons、注册 service worker），可装到桌面与移动端主屏
- **app shell 预缓存**：build 时收集应用骨架，二次打开秒开、断网仍能打开壳子
- **数据不缓存**：`/api/*` 与地图瓦片一律走网络，不做离线数据访问（最小集精神）
- **更新可控**：`prompt` 模式，新版本部署后由用户主动刷新，避免自动刷新打断用户填表丢数据
- **开箱即用**：nginx 模板补 service worker / manifest 的 no-cache header，docker 部署后 PWA 更新机制直接生效

## 设计

### 1. 技术选型与集成骨架

选用 Vite 生态标配的 [`vite-plugin-pwa`](https://vite-pwa-org.netlify.app/)（底层 Workbox `generateSW`）。build 时自动产出 `manifest.webmanifest` 与 `sw.js`，并注入注册逻辑，[main.ts](frontend/src/main.ts) 与 [index.html](frontend/index.html) 基本不动。

`vite-plugin-pwa` 作为 devDependency，在 [vite.config.ts](frontend/vite.config.ts) 的 `plugins` 数组中挂载：

```ts
import { VitePWA } from 'vite-plugin-pwa'

plugins: [
  vue(),
  vuetify({ autoImport: true }),
  VitePWA({
    registerType: 'prompt',          // 检测新版本弹提示，用户主动刷新；不用 autoUpdate 防丢表单
    injectRegister: 'auto',          // 自动注入 SW 注册脚本，无需手写
    devOptions: { enabled: true },   // vite dev 下 localhost（安全上下文）即可测安装
    includeAssets: ['favicon.ico', 'favicon.svg', 'apple-touch-icon.png'],
    manifest: { /* 见第 2 节 */ },
    workbox: { /* 见第 4 节 */ },
  }),
],
```

**三个关键开关的理由**：

- `registerType: 'prompt'`：本项目核心写操作是「记价格」，用户可能正在 QuickFillView 等表单页填写；autoUpdate 会在新 SW 接管时自动刷新页面、丢失未保存输入。prompt 让用户择机刷新
- `devOptions.enabled`：`vite dev` 下也能在 localhost 验证安装流程，无需每次 build
- `injectRegister: 'auto'`：注册脚本由插件注入 index.html，省去手动 `navigator.serviceWorker.register`

### 2. Web App Manifest

| 字段 | 值 | 说明 |
|---|---|---|
| `name` | `生计 - 生活成本计算器` | 全名，安装对话框/应用商店用 |
| `short_name` | `生计` | 桌面/主屏图标下短名（≤12 字符建议） |
| `description` | `记录商品价格、计算烹饪与生活成本` | 安装提示展示 |
| `lang` | `zh-CN` | |
| `dir` | `ltr` | |
| `display` | `standalone` | 无浏览器外壳，类原生体验 |
| `orientation` | `portrait` | 记账类以竖屏为主 |
| `scope` | `/` | |
| `start_url` | `/` | |
| `theme_color` | `#558B2F` | 橄榄绿 primary（[vuetify.ts](frontend/src/plugins/vuetify.ts#L13)），状态栏/标题栏色 |
| `background_color` | `#FDFCF8` | 温暖米白（[vuetify.ts](frontend/src/plugins/vuetify.ts#L37)），启动屏背景 |
| `icons` | 见下 | |

`theme_color` / `background_color` 取浅色主题值。manifest 只能声明一组固定色，深色模式下系统自行处理状态栏，取主品牌色即可。

`icons` 数组（由第 3 节生成，产物路径相对 `public/`）：

```ts
icons: [
  { src: 'pwa-192x192.png',    sizes: '192x192', type: 'image/png', purpose: 'any' },
  { src: 'pwa-512x512.png',    sizes: '512x512', type: 'image/png', purpose: 'any' },
  { src: 'maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
],
```

- `any` 版：圆角矩形透明底，主用途
- `maskable` 版：背景填满全图、内容缩进中心 ~80% 安全区，适配安卓各种裁剪形状

### 3. 图标资源方案

**logo 设计**（路径化 SVG 源 `frontend/src/assets/logo.svg`）：

- 1024×1024 方形画布
- 圆角矩形底（圆角约 22%），底色橄榄绿 `#558B2F`
- 前景「生计」二字横排居中，米白 `#FDFCF8`，字形源自思源黑体 Bold 字重
- **「生计」二字在 SVG 中以矢量路径 `<path>` 存在（转曲），不引用任何字体**——见下方「字体处理」
- 两套：标准版（圆角透明底，for `any`）+ maskable 版（背景填满、字缩进安全区）

**字体处理（不随仓库分发）**：思源黑体（Source Han Sans SC，Adobe + Google 联合出品，SIL OFL 免费可商用）；明确不用微软雅黑（方正/微软商业授权，有版权风险）。思源黑体**仅在制作 logo.svg 阶段使用一次**——用转曲工具（opentype.js / fonttools / Inkscape 任选）把「生计」二字字形 dump 为矢量路径写入 SVG。**转曲完成后字体文件即弃置，不放入仓库**（置于本地路径或 `.gitignore` 的临时目录，仅制作时引用）。

仓库只保留路径化的 `logo.svg`（几 KB，纯路径无字体引用）+ 由其生成的 PNG。仓库干净、无字体分发负担、无需附字体 LICENSE，生成的 PNG 位图自包含、不依赖字体。

**生成工具**：PWA 官方配套 `@vite-pwa/assets-generator`（devDependency）。单一 SVG 源 → 一条命令产出全套位图，源文件唯一（DRY，将来换 logo 只改一个 SVG 重跑）。配置 `pwa-assets.config.ts` 指定 `inputDir` / `outputDir`（`public/`），覆盖以下尺寸：

| 产物 | 尺寸 | 用途 |
|---|---|---|
| `pwa-192x192.png` | 192×192 | PWA 标准图标（any） |
| `pwa-512x512.png` | 512×512 | PWA 标准图标（any） |
| `maskable-512x512.png` | 512×512 | 安卓自适应裁剪（maskable） |
| `favicon.ico` / `favicon.svg` | 16/32 | 浏览器标签，替换不存在的 `/vite.svg` |
| `apple-touch-icon.png` | 180×180 | iOS 添加到主屏 |

[index.html](frontend/index.html#L5) 的 `<link rel="icon" href="/vite.svg">` 替换为 favicon + apple-touch-icon 引用。

### 4. Service Worker 缓存策略与边界

**预缓存（precache，build 时收集，离线可用）**——Workbox `globPatterns` 收集打包产物：

```ts
workbox: {
  globPatterns: ['**/*.{js,css,html,png,ico,svg,webmanifest,woff2}'],
  navigateFallback: 'index.html',
  // navigateFallbackDenylist 不必配：Workbox navigateFallback 仅拦截
  // Request.mode === 'navigate'（文档导航）；/api/* 是 fetch/cors，不受影响
},
```

- app shell：`index.html` + 打包 JS/CSS + manifest + 图标 + Vuetify/Leaflet 本地字体图标
- navigation 兜底：离线时任何路由导航请求返回缓存的 `index.html`——**壳子能开，页面内 API 数据加载失败属正常**，各页既有加载态/错误提示接管，SW 不做离线 fallback 页

**运行时——一律不缓存**（最小集关键边界）：

- `/api/*` 全 passthrough：不配 `runtimeCaching`，SW 对非 precache 资源默认透传网络
- 地图瓦片（高德/百度/腾讯/OSM）绝不缓存：量巨大、时效性强
- 不做 Background Sync、不做离线写、不做离线 fallback 页

### 5. 更新提示组件

新建 `frontend/src/components/common/PWAUpdatePrompt.vue`，挂载到 [App.vue](frontend/src/App.vue) 的 `<v-app>` 内，与既有 `GlobalSnackbar` / `GlobalConfirmDialog` 并列（SRP，独立组件）。

核心用 `vite-plugin-pwa` 的 `useRegisterSW`（from `virtual:pwa-register/vue`）：

```vue
<script setup lang="ts">
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { needRefresh, updateServiceWorker } = useRegisterSW({
  onOfflineReady() {
    // 静默：最小集不强调离线，不打扰用户
  },
})

const close = () => { needRefresh.value = false }
</script>

<template>
  <v-snackbar :model-value="needRefresh" timeout="-1" color="primary">
    发现新版本
    <template #actions>
      <v-btn variant="text" @click="updateServiceWorker(true)">刷新</v-btn>
      <v-btn variant="text" @click="close">稍后</v-btn>
    </template>
  </v-snackbar>
</template>
```

- `needRefresh` 为真时弹 `v-snackbar`（不自动关闭 `timeout="-1"`），「刷新」按钮调 `updateServiceWorker(true)` 重载加载新 SW，「稍后」仅关闭提示（下次刷新再弹）
- `offlineReady`（首次 SW 就绪、可离线）**静默**，最小集不强调离线，不弹提示

**类型声明**：新建 `frontend/src/env.d.ts`（项目当前无自己的 `.d.ts`，[tsconfig.json](frontend/tsconfig.json#L29) `include` 已含 `src/**/*.d.ts`）：

```ts
/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/vue" />
```

（顺带补 `vite/client`——Vite 项目标准做法，项目目前缺。）

### 6. nginx 模板：service worker no-cache

现有 [nginx 模板](deploy/nginx/default.conf.template#L35) 的 `location ~* \.(?:js|css|...)$` 会匹配 `sw.js`（`.js` 后缀）→ 命中 30 天 immutable 长缓存，**致 SW 更新机制失效**（浏览器死缓存旧 SW，prompt 永不触发）。在模板 `server` 块靠前位置补两个精确匹配 `location`（`=` 精确匹配优先级高于正则 `~*`，可盖过 `.js` 长缓存规则）：

```nginx
# service worker 与 manifest 绝不能被长缓存，否则更新永远不生效
location = /sw.js {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    expires off;
}
location = /manifest.webmanifest {
    add_header Cache-Control "no-cache";
    expires off;
}
```

仅这两段，不涉及 TLS/证书配置（仍归开发者部署时处理）。

### 7. 部署文档

在 [docs/admin/deploy.md](docs/admin/deploy.md) 新增「PWA / HTTPS 部署」一节，内容：

1. PWA 必须跑在 HTTPS 下（localhost 例外，开发可直测）
2. HTTPS 接入示例（Caddy 自动 TLS / nginx + Let's Encrypt，任选）
3. service worker / manifest 的 `no-cache` nginx 配置（即第 6 节，供非 docker 部署参考）
4. 静态资源仍走现有长缓存规则
5. 验收：Lighthouse PWA 审计 installable ✓

## 范围界定（不碰）

- ❌ 不缓存 `/api/*` 数据、不做离线数据浏览
- ❌ 不做 Background Sync / 离线写 / 离线 fallback 页
- ❌ 不配置 HTTPS 证书 / TLS（文档指引，开发者部署时配）
- ❌ 不加前端单测框架（项目当前无，[package.json](frontend/package.json) 仅 dev/build/preview），PWA 逻辑靠 Lighthouse + 手动验收覆盖
- ❌ 后端零改动（纯前端 + 部署模板）
- ❌ 不缓存地图瓦片

## 测试策略

- **构建验证**（项目硬要求，[CLAUDE.md](CLAUDE.md) 明文）：`npm run build` 通过、无 TS 报错
- **Lighthouse PWA 审计**：Chrome DevTools → Lighthouse → PWA 类别，验证 installable
- **手动验收**：dev 安装、build 部署安装、断网开壳子、prompt 更新
- 后端无改动，无后端测试负担
- **不在对话中启动服务**（[CLAUDE.md](CLAUDE.md) 规矩，开发者已开自动重载）；Lighthouse / 安装验收由开发者在已开的浏览器执行，本设计仅给步骤

## 验证标准

| # | 项 | 验证方式 |
|---|---|---|
| 1 | 构建通过 | `npm run build` 绿、无 TS 报错 |
| 2 | 可安装（PWA 金标准） | Lighthouse PWA 审计 installable ✓ |
| 3 | dev 可测安装 | `devOptions.enabled` 下 localhost 安装到桌面/主屏 |
| 4 | app shell 离线可开 | 断网 → 仍能打开壳子；API 数据加载失败属正常 |
| 5 | 二次打开秒开 | precache 命中，无白屏等待 |
| 6 | prompt 更新生效 | 部署新版本 → 刷新触发 `needRefresh` → 弹提示 → 点刷新加载新 SW |
| 7 | nginx 模板合法 | envsubst 后 `nginx -t` 或 docker build 通过（新 `location =` 块语法正确） |
