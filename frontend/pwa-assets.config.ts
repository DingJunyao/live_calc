import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

export default defineConfig({
  // 源：Task 2 生成的路径化 logo（背景已填满橄榄绿 #558B2F，字居中留白 ~22%）
  // 放 public/：assets-generator 产物与源同目录，图标需在 public/ 才能被 manifest 根路径引用
  images: ['public/logo.svg'],
  preset: {
    ...minimal2023Preset,
    // 源背景已填满 + 字居中留白充足（已超 maskable 安全区），无需额外 padding；
    // 若加 padding，padding 区会露出非主题色背景，maskable 裁剪后露白边
    maskable: { ...minimal2023Preset.maskable, padding: 0 },
  },
})
