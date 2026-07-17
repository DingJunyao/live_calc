# 前端 PWA 最小集适配

> 日期：2026-07-18
> 状态：代码完成，待开发者 Lighthouse / 安装 / 离线 / prompt 验收

## 背景

前端 Vue 3 + Vite 5 此前无任何 PWA 配置（无 manifest / service worker / logo，[public/](../frontend/public/) 空），需适配为可安装 PWA。经 brainstorming 拍板**最小集**目标：可安装到桌面/主屏 + app shell 预缓存（断网能开壳子、二次打开秒开），**不做**离线数据访问 / Background Sync / 离线写。

- spec：[2026-07-17-前端PWA适配-design.md](../docs/superpowers/specs/2026-07-17-前端PWA适配-design.md)
- plan：[2026-07-17-前端PWA适配.md](../docs/superpowers/plans/2026-07-17-前端PWA适配.md)

## 方案

- **vite-plugin-pwa 1.3.0**（底层 Workbox `generateSW`）自动产 `manifest.webmanifest` + `sw.js`：`registerType: 'prompt'`（新版本弹提示让用户主动刷新，不用 autoUpdate 防丢价格表单）+ `devOptions.enabled`（dev 可测安装）+ `injectRegister: 'auto'`
- **app shell 预缓存**：`workbox.globPatterns` 收集 index.html / JS / CSS / 图标；`navigateFallback: 'index.html'`（离线 navigation 兜底开壳子）
- **数据不缓存**（最小集关键边界）：`/api/*` 与地图瓦片 passthrough 走网络，不配 `runtimeCaching`
- **思源黑体转曲 logo**：fontTools 脚本把「生计」二字字形 dump 为 SVG `<path>`（路径化、无字体引用），字体文件不入仓库（`scripts/.fonts/` gitignore，用完即弃）；`@vite-pwa/assets-generator` 从 SVG 产全套图标
- **prompt 更新提示**：[PWAUpdatePrompt.vue](../frontend/src/components/common/PWAUpdatePrompt.vue)（`useRegisterSW` + `v-snackbar`「发现新版本，刷新以更新」）挂 [App.vue](../frontend/src/App.vue)
- **nginx no-cache**：[nginx 模板](../deploy/nginx/default.conf.template) 加 `location = /sw.js` + `location = /manifest.webmanifest`（`=` 精确匹配盖过 `*.js` 正则长缓存），防 SW 更新失效

## 主题色

`theme_color` `#558B2F`（橄榄绿 primary）、`background_color` `#FDFCF8`（米白），对齐 [vuetify.ts](../frontend/src/plugins/vuetify.ts) lightTheme。

## 执行纠偏（plan 假设 vs 实际，6 处）

1. **subagent 回退 inline**：subagent-driven 执行时 subagent 两次失败（「模型不存在」+ 意外中断），按 CLAUDE.md 老规矩回退 inline，姐姐亲手做 + 每步 fresh-eye review（与历史上多次「subagent 模型坏回退 inline」一致）
2. **fontTools 类名**：plan 写 `SvgPathPen` 错，fontTools 4.x 实为 `SVGPathPen`（全大写 SVG）
3. **assets-generator 版本**：装的是 **antfu 维护的 1.0.2**（非 vite-pwa 官方 0.x），preset 用 **`minimal2023Preset`**（非 plan 写的 `minimal2021Preset`，那是官方 0.x 的）；`UserConfig.images` 是源路径、`preset` 可传字符串（`'minimal-2023'`）或 Preset 对象；产物默认名 `pwa-<w>x<h>.png` / `maskable-icon-<w>x<h>.png` / `apple-touch-icon-<w>x<h>.png`
4. **logo.svg 源位置**：plan 假设 `src/assets/`，实际 assets-generator **产物与源同目录**，图标需在 `public/` 才能被 manifest 根路径引用 → 源改放 [public/logo.svg](../frontend/public/logo.svg)（generator 给的 head links 用根路径 `/favicon.ico` `/logo.svg` 印证此设计）
5. **manifest icons 含 64**：generator 默认产 `pwa-64x64.png`，manifest icons 共 4 条（64/192/512 any + 512 maskable）
6. **maskable padding 0**：源背景已填满橄榄绿、字居中留白 ~22%（已超 maskable 安全区），不加 padding——若加 padding，padding 区会露非主题色背景，裁剪后翻车

## 关键文件

**新建**：
- [scripts/generate_pwa_logo.py](../scripts/generate_pwa_logo.py) — fontTools 转曲脚本（`uv run --no-project --with fonttools python ...` 临时跑，不污染 .venv）
- [frontend/public/](../frontend/public/) — logo.svg + pwa-64/192/512.png + maskable-icon-512x512.png + apple-touch-icon-180x180.png + favicon.ico
- [frontend/pwa-assets.config.ts](../frontend/pwa-assets.config.ts) — assets-generator 配置（minimal2023Preset + maskable padding 0）
- [frontend/src/env.d.ts](../frontend/src/env.d.ts) — `vite/client` + `vite-plugin-pwa/vue` 类型声明（项目原无自己的 .d.ts，顺带补 vite/client）
- [frontend/src/components/common/PWAUpdatePrompt.vue](../frontend/src/components/common/PWAUpdatePrompt.vue)

**修改**：
- [frontend/package.json](../frontend/package.json) — 加 devDeps（vite-plugin-pwa + @vite-pwa/assets-generator）+ `generate-pwa-assets` script
- [frontend/vite.config.ts](../frontend/vite.config.ts) — 挂 VitePWA（manifest + workbox + devOptions）
- [frontend/index.html](../frontend/index.html) — favicon 三连（favicon.ico + logo.svg + apple-touch-icon），替换不存在的 /vite.svg
- [frontend/src/App.vue](../frontend/src/App.vue) — 挂 PWAUpdatePrompt
- [deploy/nginx/default.conf.template](../deploy/nginx/default.conf.template) — sw.js / manifest no-cache
- [docs/admin/deploy.md](../docs/admin/deploy.md) — 加「PWA / HTTPS 部署」节
- [.gitignore](../.gitignore) — `scripts/.fonts/`

## 离线壳子测试坑（重要）

**必须用生产构建测**：`npm run build` + `npm run preview`（localhost:4173），**不能用 dev 模式**。dev 模式 SW 的 precache / navigateFallback 不可靠（vite dev server 动态资源、index.html 模板注入没全进 precache），Offline 刷新直接 `ERR_INTERNET_DISCONNECTED`——这不是 bug，是 dev SW 能力所限。

preview 测离线正确步骤：访问 preview 地址 → F12 Application → Service Workers 确认 **activated and is running** → **刷新一次**（首次访问页面在 SW 注册前加载、不受控，必须 reload）→ 勾 Offline → 刷新 → 壳子能开（API 数据失败属正常）。

## 验证

- 每个 task 后 `npm run build` 通过，最终 34.30s，PWA v1.3.0 `generateSW`，precache **112 条**（4077 KiB），dist 含 `manifest.webmanifest` + `sw.js` + `registerSW.js` + `workbox-<hash>.js`
- dist/sw.js grep 确认 `index.html` 进 precache、NavigationRoute 绑定（`createHandlerBoundToURL("index.html")`，`navigateFallback` 字面不出现是 Workbox v7 编译常态，非缺失）
- 待开发者：Lighthouse PWA **installable**、localhost 安装、断网开壳子、prompt 更新、docker build nginx 模板语法

## 遗留

- 思源黑体 Bold OTF 在 `scripts/.fonts/`（gitignore 不入仓库）；换 logo 需重跑 `generate_pwa_logo.py`（字体需放回 .fonts/）+ `npm run generate-pwa-assets`
- HTTPS 生产部署：nginx 模板只加了 SW/manifest no-cache，TLS 证书由部署者配（[deploy.md](../docs/admin/deploy.md) PWA/HTTPS 节有 Caddy/Let's Encrypt 指引）
