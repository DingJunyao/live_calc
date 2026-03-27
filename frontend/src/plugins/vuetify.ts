// plugins/vuetify.ts
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// 温暖生活主题 - 浅色模式
const lightTheme = {
  dark: false,
  colors: {
    // 主色调 - 橄榄绿（健康、自然）
    primary: '#558B2F',
    'on-primary': '#FFFFFF',
    'primary-container': '#DCE8CC',
    'on-primary-container': '#141E07',

    // 辅助色 - 天蓝（数据、理性）
    secondary: '#547C8C',
    'on-secondary': '#FFFFFF',
    'secondary-container': '#D5E6F0',
    'on-secondary-container': '#121F27',

    // 第三色 - 琥珀橙（价格、成本）
    tertiary: '#B07B0B',
    'on-tertiary': '#FFFFFF',
    'tertiary-container': '#FDD86B',
    'on-tertiary-container': '#281900',

    // 错误色
    error: '#BA1A1A',
    'on-error': '#FFFFFF',
    'error-container': '#FFDAD6',
    'on-error-container': '#410002',

    // 背景 - 温暖米白
    background: '#FDFCF8',
    'on-background': '#1B1C18',
    surface: '#FDFCF8',
    'on-surface': '#1B1C18',
    'surface-variant': '#EBE7DD',
    'on-surface-variant': '#4A473E',

    outline: '#7B776F',
    'outline-variant': '#CAC6BD',
  },
}

// 深色模式 - 夜间护眼
const darkTheme = {
  dark: true,
  colors: {
    primary: '#B0CB94',
    'on-primary': '#253510',
    'primary-container': '#3B4D25',
    'on-primary-container': '#DCE8CC',

    secondary: '#B9CBD6',
    'on-secondary': '#1F313D',
    'secondary-container': '#354854',
    'on-secondary-container': '#D5E6F0',

    tertiary: '#FBC02D',
    'on-tertiary': '#3E2E00',
    'tertiary-container': '#5A4300',
    'on-tertiary-container': '#FDD86B',

    error: '#FFB4AB',
    'on-error': '#690005',
    'error-container': '#93000A',
    'on-error-container': '#FFDAD6',

    background: '#1B1C18',
    'on-background': '#E3E3DB',
    surface: '#1B1C18',
    'on-surface': '#E3E3DB',
    'surface-variant': '#4A473E',
    'on-surface-variant': '#CAC6BD',

    outline: '#949088',
    'outline-variant': '#4A473E',
  },
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: lightTheme,
      dark: darkTheme,
    },
  },
  display: {
    // 自定义断点配置
    // 将 mobile 断点修改为 smAndDown (< 600px)
    // 默认是 mdAndDown (< 1280px)，对于侧边栏来说太大了
    mobileBreakpoint: 'sm',
    thresholds: {
      xs: 0,
      sm: 600,
      md: 960,
      lg: 1280,
      xl: 1920,
      xxl: 2560,
    },
  },
})
