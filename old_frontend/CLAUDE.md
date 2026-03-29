# 生计 - 前端模块 (Vue 3)

## 概述

前端模块是一个基于 Vue 3 和 Vite 构建的现代化 Web 应用，提供了用户友好的界面来交互后端 API，实现生活成本管理功能。

## 目录结构

```
frontend/
├── src/
│   ├── api/          # API 客户端与请求封装
│   │   └── client.ts # 通用 API 客户端
│   ├── assets/       # 静态资源
│   ├── components/   # 可复用的 UI 组件
│   ├── stores/       # Pinia 状态管理
│   │   └── user.ts   # 用户状态管理
│   ├── views/        # 页面视图组件
│   │   ├── auth/     # 认证相关页面
│   │   │   ├── Login.vue
│   │   │   └── Register.vue
│   │   ├── dashboard/ # 仪表盘页面
│   │   │   ├── Dashboard.vue
│   │   │   └── QuickAdd.vue
│   │   ├── products/  # 产品管理页面
│   │   │   └── ProductList.vue
│   │   ├── recipes/   # 菜谱管理页面
│   │   │   └── RecipeList.vue
│   │   ├── locations/ # 地点管理页面
│   │   │   └── LocationMap.vue
│   │   └── reports/   # 报告统计页面
│   │       └── ReportOverview.vue
│   ├── router/       # 路由配置
│   │   └── index.ts
│   ├── styles/       # 全局样式
│   │   └── main.css
│   └── main.ts       # 应用入口
├── public/           # 静态资源
├── index.html        # 应用入口 HTML
├── package.json      # 依赖管理
├── vite.config.ts    # Vite 构建配置
└── tsconfig.json     # TypeScript 配置
```

## 核心功能模块

### 认证模块 (auth)
- 用户登录页面
- 用户注册页面
- 表单验证与错误处理
- SHA256 密码预处理
- 邀请码需求检测

### 仪表盘模块 (dashboard)
- 个性化欢迎界面
- 统计数据展示（月支出、记录数、菜谱数等）
- 快捷操作卡片
- 最近记录展示
- 实时数据加载

### 产品管理模块 (products)
- 产品价格记录列表
- 价格历史查看
- 多条件筛选与搜索
- 添加产品记录功能

### 菜谱管理模块 (recipes)
- 菜谱创建与编辑
- 成本与营养分析
- 菜谱分类与标签管理
- 智能配料推荐

### 地点管理模块 (locations)
- 地点列表与地图显示
- 路线规划与距离计算
- 收藏地点管理
- 位置搜索功能

### 报告统计模块 (reports)
- 支出报告展示
- 价格趋势分析
- 数据可视化图表
- 报告导出功能

## 技术实现

### 状态管理 (Pinia)
- `userStore` - 管理用户认证状态
- 用户信息持久化
- 令牌自动刷新机制
- 登录/登出逻辑处理

### API 客户端 (client.ts)
- 统一的请求/响应拦截器
- 自动令牌附带
- 错误处理机制
- 请求取消支持

### 路由管理 (Vue Router)
- 懒加载页面组件
- 路由守卫（认证保护）
- 动态路由参数

### 组件设计
- 响应式设计（移动端适配）
- 组件化开发模式
- Props 验证
- 事件规范化

## UI/UX 设计

### 设计原则
- 简洁直观的界面
- 一致的视觉风格
- 高效的信息展示
- 良好的用户引导

### 色彩方案
- 主色调: #42b883 (绿色，代表成长与健康)
- 辅助色: #f5f5f5 (背景色)
- 状态色: 红色(#c33)、绿色(#42b883)、蓝色(#667eea)

### 响应式布局
- Flexbox 和 Grid 布局
- 移动优先设计
- 断点设置: xs, sm, md, lg, xl

## API 集成

### 认证 API
- `/api/v1/auth/login` - 用户登录
- `/api/v1/auth/register` - 用户注册
- `/api/v1/auth/refresh` - 令牌刷新
- `/api/v1/auth/me` - 获取用户信息
- `/api/v1/auth/config` - 获取注册配置

### 业务 API
- `/api/v1/products/` - 产品管理
- `/api/v1/locations/` - 地点管理
- `/api/v1/nutrition/` - 营养数据
- `/api/v1/recipes/` - 菜谱管理
- `/api/v1/reports/` - 报告统计

## 构建与部署

### 构建配置 (vite.config.ts)
- TypeScript 支持
- Vue 3 编译支持
- PWA 插件集成
- 代理配置（开发环境）

### PWA 支持
- Service Worker
- Manifest 配置
- 离线缓存
- 安装提示

### 依赖管理
- Vue 3 + Composition API
- Vue Router 4
- Pinia 2
- TypeScript 5
- Tailwind CSS 或原生 CSS

## 开发规范

### Vue 组件规范
- 使用 Composition API
- TypeScript 类型注解
- Props 验证与默认值
- 组件命名采用 PascalCase

### 代码规范
- 使用 Prettier 格式化代码
- ESLint 代码检查
- 单文件组件 (SFC) 结构
- 模板中的属性顺序标准化

### 路由约定
- 路由名称使用 kebab-case
- 页面组件放置在 views 目录
- 路由参数类型声明

### 状态管理规范
- Store 使用模块化组织
- Action 命名采用动词开头
- State 类型定义明确
- 数据持久化合理使用

## 安全考虑

### 客户端安全
- 密码 SHA256 哈希预处理
- 令牌存储在 localStorage
- XSS 防护（DOM 消毒）
- CSRF 保护（令牌验证）

### 数据安全
- 敏感数据不缓存
- 请求参数验证
- 响应数据净化

## 性能优化

### 加载优化
- 路由懒加载
- 组件按需加载
- 图片懒加载
- 代码分割

### 渲染优化
- 虚拟滚动（长列表）
- 防抖节流（搜索输入）
- 缓存策略（API 响应）
- 组件复用（v-memo）

## 测试策略

### 单元测试
- 组件单元测试 (Vue Test Utils)
- Store 逻辑测试
- 工具函数测试

### 集成测试
- 组件交互测试
- API 集成测试
- 路由守卫测试

### 端到端测试
- 关键用户流程测试
- 表单提交测试
- 认证流程测试