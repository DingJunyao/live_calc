# Vuetify 迁移设计方案

## 概述

将前端从原生 CSS 迁移到 Vuetify 3 组件库，以提升维护便捷性、样式稳定性，并更好地支持移动端、PWA 和夜间模式。

## 需求总结

| 项目 | 需求 |
|------|------|
| 组件库 | Vuetify 3 |
| 平台 | 桌面端 + 移动端 + PWA |
| 夜间模式 | 跟随系统 + 手动开关 |
| 特殊组件 | 保留 ECharts + Leaflet |
| 迁移策略 | 一次性重写 |
| 小程序 | 暂不支持，未来预留 |

## 技术架构

### 核心技术栈

```
Vue 3.4+ / TypeScript 5.3+
    ↓
Vuetify 3.4+ (Material Design 3)
    ↓
Vite 5+ (构建工具)
    ↓
vite-plugin-pwa (PWA 支持)
```

### 保留组件

| 组件 | 版本 | 用途 |
|------|------|------|
| ECharts | 6.0+ | 价格趋势图、成本分析图 |
| Leaflet | 1.9+ | 地图显示、位置选择 |
| leaflet.chinatmsproviders | 3.0+ | 国内地图服务适配 |
| @mdi/font | 7.4+ | 图标（Vuetify 默认） |

### 新增依赖

| 依赖 | 用途 |
|------|------|
| vuetify | 组件库核心 |
| @vuetify/vite-plugin | Vite 构建插件 |
| sass | Vuetify 主题定制需要 |
| date-fns | 日期处理（Vuetify 内部使用） |

### 移除项

- 所有自定义 CSS 文件（`style.css`、`performance-optimization.css` 等）
- 手写的分页、表单、模态框等通用组件

## 主题系统

### 色彩方案设计

**浅色模式**
```
主色:     #1976D2 (蓝色 - 延续 Material Design 经典)
辅助色:   #4CAF50 (绿色 - 呼应原有 #42b883 的健康主题)
警告色:   #FF9800 (橙色)
错误色:   #F44336 (红色)
背景色:   #FAFAFA (浅灰)
表面色:   #FFFFFF (白色卡片)
```

**深色模式**
```
主色:     #90CAF9 (浅蓝 - 深色模式下降低饱和度)
辅助色:   #81C784 (浅绿)
背景色:   #121212 (Material Design 深色标准)
表面色:   #1E1E1E (卡片背景)
```

### 主题切换逻辑

```typescript
// 优先级：用户手动设置 > 系统偏好 > 默认浅色
const themeMode = useStorage('theme-mode', 'system') // 'light' | 'dark' | 'system'

// 监听系统变化
const prefersDark = usePreferredDark()

// 计算实际主题
const actualTheme = computed(() => {
  if (themeMode.value === 'system') {
    return prefersDark.value ? 'dark' : 'light'
  }
  return themeMode.value
})
```

### 持久化

- 用户主题偏好存储在 `localStorage`
- 登录后同步到后端用户设置（可选）

## 目录结构与组件映射

### 新目录结构

```
frontend/src/
├── plugins/
│   └── vuetify.ts          # Vuetify 配置 + 主题定义
├── composables/
│   └── useTheme.ts         # 主题切换逻辑
├── components/
│   ├── common/             # 通用业务组件（非 Vuetify）
│   │   ├── NutritionProgressBar.vue
│   │   └── NutritionDisplay.vue
│   └── map/                # 地图组件（保留）
│       ├── AMapPicker.vue
│       ├── BMapPicker.vue
│       └── TencentMapPicker.vue
├── layouts/
│   ├── DefaultLayout.vue   # 带导航栏的标准布局
│   └── AuthLayout.vue      # 登录/注册页面布局
└── views/                  # 页面组件（使用 Vuetify 重写）
    └── ...
```

### 组件映射表（通用 UI 组件 → Vuetify）

| 原组件 | Vuetify 替代 |
|--------|--------------|
| `Pagination.vue` | `<v-pagination>` |
| `ProductModal.vue` | `<v-dialog>` + `<v-card>` |
| `PageHeader.vue` | `<v-toolbar>` 或 `<v-app-bar>` |
| 手写表单 | `<v-form>` + `<v-text-field>` 等 |
| 手写按钮 | `<v-btn>` |
| 手写表格 | `<v-data-table>` |
| 手写卡片 | `<v-card>` |
| 手写标签页 | `<v-tabs>` |

### 删除的文件

- `src/style.css`
- `src/styles/performance-optimization.css`
- `src/styles/product-modal-fix.css`
- `src/components/Pagination.vue`
- `src/components/ProductModal.vue`
- `src/components/PageHeader.vue`

## 页面布局设计

### 全局布局结构

```
┌─────────────────────────────────────────────┐
│  <v-app-bar>                                │
│  ├─ Logo + 应用名称                          │
│  ├─ 搜索框（可选）                            │
│  └─ 主题切换按钮 + 用户菜单                    │
├─────────────────────────────────────────────┤
│  <v-navigation-drawer>                      │
│  ├─ 仪表盘                                   │
│  ├─ 商品管理                                 │
│  ├─ 菜谱管理                                 │
│  ├─ 营养数据                                 │
│  ├─ 报告统计                                 │
│  └─ 管理员（仅管理员可见）                     │
├─────────────────────────────────────────────┤
│  <v-main>                                   │
│  │  页面内容区域                              │
│  │  （带 <v-container> 响应式内边距）          │
│  └─                                         │
├─────────────────────────────────────────────┤
│  <v-footer>（可选）                          │
└─────────────────────────────────────────────┘
```

### 响应式断点策略

| 断点 | Vuetify | 导航栏 | 布局调整 |
|------|---------|--------|----------|
| 手机 | `< 600px` (xs) | 底部导航栏 | 单列布局 |
| 平板 | `600-960px` (sm) | 抽屉式导航 | 两列布局 |
| 桌面 | `960-1280px` (md) | 固定侧边栏 | 多列布局 |
| 大屏 | `> 1280px` (lg/xl) | 固定侧边栏 | 最大宽度限制 |

### 移动端特殊处理

- **底部导航栏**：使用 `<v-bottom-navigation>` 替代侧边栏
- **FAB 按钮**：关键操作使用悬浮按钮 `<v-fab>`
- **全屏模态框**：移动端表单使用 `<v-dialog fullscreen>`
- **手势支持**：侧滑打开导航抽屉

## 迁移阶段划分

### 阶段规划

```
阶段 1：基础设施（1-2 天）
├── 安装 Vuetify 依赖
├── 配置 vuetify.ts 插件
├── 设计并配置主题系统
├── 创建布局组件（DefaultLayout、AuthLayout）
└── 验证主题切换功能

阶段 2：认证模块（1 天）
├── 重写 Login.vue
├── 重写 Register.vue
└── 验证表单验证逻辑

阶段 3：核心业务模块（3-4 天）
├── Dashboard.vue + QuickAdd.vue
├── ProductList.vue + ProductManage.vue
├── ItemDetail.vue（含价格图表、营养显示）
└── 验证 ECharts 集成

阶段 4：菜谱模块（2-3 天）
├── RecipeList.vue
├── RecipeDetail.vue（含成本图表）
├── RecipeForm.vue
└── 验证营养计算显示

阶段 5：其他模块（2 天）
├── NutritionDetail.vue
├── ReportOverview.vue
├── MerchantMap.vue
├── AdminPanel 相关页面
└── 验证 Leaflet 地图集成

阶段 6：收尾（1 天）
├── 移动端适配测试
├── PWA 功能验证
├── 暗色模式全页面测试
└── 性能优化
```

### 预计总工期：10-13 天

## 风险与注意事项

### 已识别风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| ECharts 样式冲突 | 图表在暗色模式下可能显示异常 | 封装 ECharts 组件，监听主题变化自动刷新 |
| Leaflet 样式冲突 | 地图控件样式可能被覆盖 | 使用 CSS 命名空间隔离 |
| 地图弹窗样式 | 信息窗口需要适配 Vuetify 风格 | 单独定义地图弹窗样式 |
| PWA 缓存策略 | 切换主题后可能缓存旧资源 | 配置版本号，主题变化时提示刷新 |
| 移动端虚拟键盘 | 表单输入时布局可能错乱 | 使用 Vuetify 内置的 `v-layout` 处理 |

### 需要注意的细节

1. **图表暗色模式**：ECharts 需要单独配置主题，不能自动跟随 Vuetify
2. **地图弹窗**：保持自定义样式，不强制使用 Vuetify 组件
3. **表单验证**：Vuetify 有自己的验证规则，需要迁移现有逻辑
4. **路由过渡动画**：使用 Vuetify 提供的过渡效果

### 不在本次迁移范围

- 后端 API 无需修改
- 数据库无需修改
- 路由结构保持不变
- Pinia Store 逻辑保持不变

## 决策记录

| 项目 | 决策 |
|------|------|
| 组件库 | Vuetify 3 |
| 主题策略 | 预设主题系统，跟随系统 + 手动切换 |
| 保留组件 | ECharts、Leaflet、地图组件 |
| 迁移方式 | 一次性重写，分 6 个阶段 |
| 预计工期 | 10-13 天 |
