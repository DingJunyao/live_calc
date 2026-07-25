# 品牌元数据（Branding）

## Logo
**源文件：** `frontend/public/logo.svg` — 以此为唯一标准，所有平台图标均由此文件生成。

## 主题色
| 用途 | 色值 |
|------|------|
| 主色 (primary) | `#558B2F`（绿色） |
| 次要色 (secondary) | `#547C8C` |
| 错误色 (error) | `#BA1A1A` |

定义位置：`mobile/lib/core/theme/app_theme.dart`

## App 名称
| 平台 | 名称 | 文件位置 |
|------|------|----------|
| Android 桌面 | 生计 | `android/app/src/main/AndroidManifest.xml:3` |
| iOS 桌面 | 生计 - 生活成本计算器 | `ios/Runner/Info.plist` (CFBundleDisplayName) |
| iOS 内部 | 生计 | `ios/Runner/Info.plist` (CFBundleName) |
| Flutter 窗口 | 生计 - 生活成本计算器 | `lib/app.dart:12` |

## 包名
`com.a4ding.livecalc`

| 文件 | 用途 |
|------|------|
| `android/app/build.gradle.kts:19` | applicationId |
| `android/app/build.gradle.kts:8` | namespace |
| `android/app/src/main/kotlin/com/a4ding/livecalc/MainActivity.kt` | Kotlin 源目录 |

## 应用版本
`mobile/pubspec.yaml` → `version: 1.0.0+1`

---

## 修改 Logo 的操作步骤

1. **替换源文件**：将新 SVG 覆盖 `frontend/public/logo.svg`

2. **生成各平台图标**（需 Node.js + sharp 库）：
   ```bash
   cd D:\code\live_calc
   npm install sharp   # 首次需要
   ```

   ```js
   // 用 Node.js 执行以下脚本生成所有图标
   const sharp = require('sharp');
   const fs = require('fs');
   const svg = fs.readFileSync('frontend/public/logo.svg');

   // Android mipmap（5 种密度）
   const sizes = { mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192 };
   for (const [density, size] of Object.entries(sizes)) {
     const png = await sharp(svg).resize(size, size).png().toBuffer();
     fs.writeFileSync(`mobile/android/app/src/main/res/mipmap-${density}/ic_launcher.png`, png);
     fs.writeFileSync(`mobile/android/app/src/main/res/mipmap-${density}/ic_launcher_round.png`, png);
   }

   // iOS AppIcon（17 个尺寸）
   // macOS AppIcon（7 个尺寸）
   // Web PWA 图标（4 个 + favicon）
   // 前端 PWA 图标（5 个）
   ```

3. **Windows 图标**：`mobile/windows/runner/resources/app_icon.ico` 需用专用工具（如 ImageMagick 或在线转换器）将 PNG 转为 .ico 格式。

4. **验证**：
   ```bash
   cd mobile
   flutter build apk --debug   # Android
   flutter build ios             # iOS（需 macOS）
   ```

5. **提交**：
   ```bash
   git add mobile/ frontend/public/*.png
   git commit -m "chore: update app icons from logo.svg"
   ```
