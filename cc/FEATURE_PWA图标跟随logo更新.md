# FEATURE：PWA 图标跟随 logo 更新

## 背景

PWA 最小集适配（见 [FEATURE_前端PWA适配.md](FEATURE_前端PWA适配.md)）时，6 个图标是基于**旧 logo**（思源黑体转曲「生计」二字生成路径化 SVG）用 `@vite-pwa/assets-generator` 生成的。

用户换了新 [logo.svg](frontend/public/logo.svg)（绿底 `#558b2f` + 白色算盘计算器几何图案，几个 `<rect>` + 一个 `<path>`，git status `M frontend/public/logo.svg`），但图标没跟着重跑，仍显示旧临时图标。

## 排查

- `frontend/package.json` 早装 `@vite-pwa/assets-generator` 1.0.2（devDep）且有 `"generate-pwa-assets": "pwa-assets-generator"` 脚本——根本不用自己装 sharp 写脚本，项目本就走官方工具。
- [pwa-assets.config.ts](frontend/pwa-assets.config.ts) 一直在。首轮 Glob 用了错误名字 `pwa-assets-generator.config.*` 没找到；README 示例确认正确约定名是 `pwa-assets.config.ts`。配置源已指向 `public/logo.svg`、maskable 已 `padding: 0`。
- `frontend/src/` 零硬编码图标引用（grep 确认）。引用仅两处：
  - [index.html](frontend/index.html)：favicon.ico / logo.svg / apple-touch-icon-180x180.png
  - [vite.config.ts](frontend/vite.config.ts) manifest：pwa-64/192/512 + maskable-icon-512x512

核心动作其实就一个：**重跑生成器**。但配置有个遗漏要顺手补。

## 改动

### 1. 配置补全 apple / transparent（[pwa-assets.config.ts](frontend/pwa-assets.config.ts)）

原配置只覆盖了 maskable，**漏了 apple**——apple 仍是默认 `padding: 0.3 + 白底`，绿色满底 logo 缩小后会变成「小绿块漂在白底中间」，iOS 主屏图标很难看。同源的毛病，补齐：

- `transparent` / `maskable` / `apple` 三类统一 `padding: 0`，让绿底原样满铺。
- `maskable` / `apple` 显式 `resizeOptions.background: '#558b2f'` 兜底（即便 padding 0 不该露背景，也设成主题绿以防万一，绝不露白）。

**默认值与覆盖机制依据**（node_modules 内）：

- [index.mjs:13-17](frontend/node_modules/@vite-pwa/assets-generator/dist/index.mjs#L13) `defaultPngOptions`：maskable / apple 默认 `{ padding: 0.3, resizeOptions: { fit: "contain", background: "white" } }`——这就是「加 padding 露白翻车」的根源。
- [index.mjs:38-45](frontend/node_modules/@vite-pwa/assets-generator/dist/index.mjs#L38) `toResolvedAsset`：`padding: defaultPngOptions[type].padding` 先填，`...asset` 后展开，故在 preset 里塞 `padding: 0` 即可覆盖默认。

### 2. 重跑生成器

`npm run generate-pwa-assets`，从 `public/logo.svg` 重生成 6 个文件：

- pwa-64x64.png / pwa-192x192.png / pwa-512x512.png
- maskable-icon-512x512.png
- apple-touch-icon-180x180.png
- favicon.ico（preset 的 `favicons: [[48, "favicon.ico"]]` 出，48×48 单分辨率）

## 文件命名对齐

`defaultAssetName`（[index.mjs:46-55](frontend/node_modules/@vite-pwa/assets-generator/dist/index.mjs#L46)）：

- transparent → `pwa-{w}x{h}.png`
- maskable → `maskable-icon-{w}x{h}.png`
- apple → `apple-touch-icon-{w}x{h}.png`

加 `minimal2023Preset.favicons`，与现有 manifest / index.html 引用一字不差，无需改 vite.config.ts 或 index.html。

## 验证

- **padding 0 生效的决定性证据**：`maskable-icon-512x512.png` 与 `pwa-512x512.png` 字节数完全相等（均 1313 字节）。若 maskable 仍是默认 padding 0.3 + 白底，像素内容（缩小绿块 + 白边）必不同于满铺绿底的 pwa-512，字节数不可能相同。
- maskable 安全区：logo 图案在中心 80% 安全区内（边缘留白 ~12.5% > 10%），padding 0 时平台 mask 只裁掉绿色边缘、不伤白色图案。
- build 通过（19.97s），PWA precache 112 entries（与改前一致），SW 正常生成。

## 复跑

以后再改 `logo.svg`，跑一次 `npm run generate-pwa-assets` 即可同步全部图标。无表结构变更，纯前端静态资源 + 一行配置补全。
