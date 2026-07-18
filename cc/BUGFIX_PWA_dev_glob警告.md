# PWA dev 模式 workbox glob 空匹配警告消除

## 症状
前端 dev 启动、访问主页时终端打印 workbox-build 警告：
```
One of the glob patterns doesn't match any files. Please remove or fix the following: {
  "globDirectory": ".../frontend/dev-dist",
  "globPattern": "**/*.{js,css,html,png,ico,svg,webmanifest,woff2}",
  "globIgnores": ["**/node_modules/**/*", "sw.js", "workbox-*.js"]
}
```

## 根因
[vite.config.ts](../frontend/vite.config.ts) 的 `workbox.globPatterns` 配的是 **build 产物类型**（js/css/html/png/svg/webmanifest/woff2），本意为 build 模式扫描 `dist`。

但 `devOptions.enabled: true` 时，vite-plugin-pwa 在 dev 模式下也会跑一遍 workbox glob，扫描对象是 `dev-dist`。dev 模式 vite 走内存提供应用资源，`dev-dist` 里**只有两个文件**：
- `sw.js`（被默认 globIgnores 的 `sw.js` 排除）
- `workbox-xxxxxxxx.js`（被默认 globIgnores 的 `workbox-*.js` 排除）

两个都被排除 → globPatterns 匹配必然为空 → workbox-build 对每个空匹配 pattern 打 warning。

良性警告：dev 模式 precache 本就无意义（资源走 vite 内存 + HMR），SW 注册与 manifest 都正常，仅终端噪音。

## 解法
vite-plugin-pwa 官方给了开关。源码 `node_modules/vite-plugin-pwa/dist/index.js:579`：
```js
const globPatterns = options.devOptions.suppressWarnings === true
  ? ["suppress-warnings.js"]
  : options.workbox.globPatterns;
```
配套逻辑（index.js:576-577）会在 dev-dist 补一个空 `suppress-warnings.js`，并把 **dev 分支**用的 globPatterns 临时改成 `["suppress-warnings.js"]`（命中那个空文件，不再空匹配）。

类型定义（index.d.ts:804-810）明确：仅 `generateSW` 策略生效；只改 dev 用 globPatterns，不动 `workbox.globPatterns`。

[vite.config.ts](../frontend/vite.config.ts) `devOptions` 加一行：
```ts
devOptions: {
  enabled: true,
  suppressWarnings: true,   // ← 新增
},
```

KISS：一行官方开关，比条件化 `globPatterns: []` 之类 hack 干净。

## 验证
- build 通过 35.92s，`precache 128 entries` 不变 → 证实 build 模式 globPatterns 与 dist precache 清单完全不受影响（suppressWarnings 只在 dev 分支读取）
- dev 模式需**手动重启 dev 服务**生效（vite 对 vite.config.ts 改动不一定自动重启）：重启后 dev-dist 多出一个空的 `suppress-warnings.js`，警告消失

## 范围
- 单文件改动 [vite.config.ts](../frontend/vite.config.ts)
- 无表结构变更，无新依赖
- 仅消 dev 模式控制台噪音，build/产物零变化
