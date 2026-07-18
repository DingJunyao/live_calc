# PWA 快捷方式图标（manifest.shortcuts）

## 背景

[vite.config.ts](frontend/vite.config.ts) 给 PWA 加了 7 个 shortcuts（今日推荐/价格记录/菜谱管理/商品管理/原料管理/商家管理/个人中心），DevTools 审计提示每个 shortcut 应包含 96×96 像素图标。

## 方案

用项目既有工具链（不引新依赖）从 MDI 字体提取侧边栏同款图标，渲染成「绿底白图标」PNG（与 logo 配色一致）：

```
@mdi/font ttf  →  fontTools 提字形 path  →  SVG（按 bounds 居中）  →  sharp  →  96×96 PNG
（已有）          （PEP 723 uv --with）        （配色对齐 logo）        （已有）
```

新增 [scripts/generate_pwa_shortcuts.py](scripts/generate_pwa_shortcuts.py)：脚本自包含（PEP 723 声明 fontTools 依赖，`uv run` 直接跑、不污染 venv），改侧边栏图标时改这里重跑即可。

## 图标对应

shortcuts 顺序、文件名、MDI 图标名与 [AppLayout.vue](frontend/src/components/layout/AppLayout.vue) 侧边栏 `prepend-icon` 一一对齐：

| shortcut | url | MDI 图标 | 文件 |
|---|---|---|---|
| 今日推荐 | / | mdi-silverware-fork-knife | today.png |
| 价格记录 | /prices | mdi-currency-cny | prices.png |
| 菜谱管理 | /recipes | mdi-book-open-variant | recipes.png |
| 商品管理 | /data/products | mdi-package-variant | products.png |
| 原料管理 | /data/ingredients | mdi-leaf | ingredients.png |
| 商家管理 | /data/merchants | mdi-store | merchants.png |
| 个人中心 | /profile | mdi-account | profile.png |

## 关键技术点

### 居中策略：按字形 bounds 几何居中

MDI 字体 `unitsPerEm=512`，advance=512。但各图标的几何 bounds 中心散在 cx 203~246、cy 171~192，明显偏离正中心 (256,256)，cy 尤其偏下（字体 baseline 偏低所致）。若直接套 em box 映射（`translate(0,512) scale(1,-1)`），图标会整体偏下。

故对每个字形按其 `(xMin,yMin,xMax,yMax)` 算平移，让几何中心落到 SVG 中心：

```python
tx = SIZE/2 - (x_max + x_min)/2
ty = SIZE/2 + (y_max + y_min)/2   # + 号因 scale(1,-1) 翻 y
transform = translate(tx, ty) scale(1, -1)
```

各字形保持原大不额外缩放——MDI 设计师已靠「内容多则 bounds 小」平衡视觉重量，原大渲染即与应用内 `<v-icon>` 视觉一致。

### 配色

对齐 [logo](frontend/public/logo.svg) / vite.config.ts `theme_color`：背景 `#558B2F`（橄榄绿 primary），前景 `#FDFCF8`（温暖米白）。

### SVG → PNG

SVG `viewBox="0 0 512 512"`（path 坐标直接用字体单位），sharp 以 `density: 600` 高 DPI 渲染再 `resize(96,96)`，缩放抗锯齿优于直接渲染 96。

## 踩坑：node `-e` 模式 argv 偏移

初版 sharp 转换脚本用 `process.argv[2]/[3]` 取 tmpDir/outDir，但 `node --input-type=module -e "<code>" arg1 arg2` 下 **没有脚本路径占 argv[1]**，参数从 `argv[1]` 开始（实测 `argv = ['node.exe', 'arg1', 'arg2']`）。多偏移一位导致 tmpDir 实际指向 outDir（刚 mkdir 的空目录），`readdir` 无 .svg、for 循环不执行、进程静默退出 0——`check=True` 拦不到，现象是目录建了却是空的。修为 `argv[1]/[2]`。

## 产物与缓存

- 7 张 PNG 落 [frontend/public/shortcuts/](frontend/public/shortcuts/)（700B~2KB 小图标）
- [vite.config.ts](frontend/vite.config.ts) shortcuts 每项加 `icons: [{ src: "shortcuts/xxx.png", sizes: "96x96", type: "image/png" }]`（src 写法对齐 screenshots 的 `screenshots/xxx.png`，相对 manifest 根）
- workbox `globPatterns` 含 `png`，shortcuts 图标自动进 precache（断网可用）
- build 通过（13.77s），PWA precache 114→128 entries

## 复跑

改侧边栏图标或配色后：

```bash
uv run scripts/generate_pwa_shortcuts.py
```

## 遗留

- shortcut 图标非 maskable（平台对 shortcut 图标不做 mask 裁剪，按 fullbleed 设计即可，无需 maskable 变体）
- DevTools「快捷键数量上限因平台而异」是通用提示，7 个在主流平台（Android/Windows）均支持，非问题
