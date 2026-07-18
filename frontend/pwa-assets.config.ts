import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

export default defineConfig({
  // 源：Task 2 生成的路径化 logo（背景已填满橄榄绿 #558B2F，字居中留白 ~22%）
  // 放 public/：assets-generator 产物与源同目录，图标需在 public/ 才能被 manifest 根路径引用
  images: ['public/logo.svg'],
  preset: {
    ...minimal2023Preset,
    // 源背景已填满橄榄绿 + 图案居中留白充足（已超 maskable 安全区），
    // 三类图标统一 padding: 0 让绿底原样满铺。
    // 默认 maskable/apple 是 padding 0.3 + 白底（见 defaultPngOptions），
    // 满底 logo 缩小后四周露一圈白会翻车，故显式置 0 + 主题绿背景兜底。
    transparent: { ...minimal2023Preset.transparent, padding: 0 },
    maskable: {
      ...minimal2023Preset.maskable,
      padding: 0,
      resizeOptions: { fit: 'contain', background: '#558b2f' },
    },
    apple: {
      ...minimal2023Preset.apple,
      padding: 0,
      resizeOptions: { fit: 'contain', background: '#558b2f' },
    },
  },
})
