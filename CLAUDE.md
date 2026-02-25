# 生计 - 生活成本计算器

## 项目概述

这是一个全栈的生活成本计算器应用，旨在帮助用户记录商品价格、计算烹饪成本、优化生活开支。

### 核心功能
- 📝 商品价格记录 - 记录不同时间、不同地点的商品价格
- 🍳 菜谱成本计算 - 根据价格记录计算菜谱成本
- 🥗 营养成分分析 - 基于 USDA 数据库的营养分析
- 📍 地图与路线规划 - 集成地图服务，计算出行成本
- 📊 生活成本报告 - 生成每日、每周、每月报告
- 💰 多币种支持 - 支持多种货币
- 🌏 多单位转换 - 支持公制/市制/英制转换
- 🔐 用户认证 - 支持 JWT 认证和邀请码注册

## 系统架构

```
live_calc/
├── backend/              # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/        # API 路由定义
│   │   ├── core/       # 核心配置与安全
│   │   ├── models/     # 数据库模型
│   │   ├── schemas/    # Pydantic 模式
│   │   ├── services/   # 业务逻辑层
│   │   └── utils/      # 工具函数
│   ├── alembic/        # 数据库迁移
│   └── tests/          # 测试用例
├── frontend/            # 前端应用 (Vue 3)
│   ├── src/
│   │   ├── api/       # API 客户端
│   │   ├── components/ # 可复用组件
│   │   ├── stores/    # Pinia 状态管理
│   │   ├── views/     # 页面视图
│   │   └── router/    # 路由配置
│   └── public/         # 静态资源
├── docker-compose.yml   # Docker 编排
└── README.md           # 项目文档
```

## 技术栈

### 后端 (FastAPI)
- **框架**: FastAPI - 现代化的 Python Web 框架
- **ORM**: SQLAlchemy - Python SQL 工具包和对象关系映射
- **迁移**: Alembic - 数据库迁移工具
- **认证**: Python-JOSE + Passlib - JWT 认证和密码哈希
- **任务调度**: APScheduler - 任务调度器
- **异步任务**: Celery（可选）- 分布式任务队列

### 前端 (Vue 3)
- **框架**: Vue 3 - 渐进式 JavaScript 框架
- **构建工具**: Vite - 新一代前端构建工具
- **状态管理**: Pinia - Vue 的官方状态管理库
- **路由**: Vue Router - 官方路由管理器
- **HTTP 客户端**: Axios - Promise 基础的 HTTP 客户端
- **地图**: Leaflet - 开源地图库
- **图表**: Chart.js - 简单灵活的图表库

### 数据库
- **开发**: SQLite - 轻量级嵌入式数据库
- **生产**: PostgreSQL / MySQL - 企业级数据库

### 容器化
- **容器**: Docker - 容器化平台
- **编排**: Docker Compose - 多容器应用编排
- **Web 服务器**: Nginx - 高性能 Web 服务器

## 模块说明

### 后端模块
- **auth** - 用户认证与授权
- **products** - 商品价格记录与历史追踪
- **locations** - 地点管理与地图服务
- **nutrition** - 营养数据库与匹配算法
- **recipes** - 菜谱管理与成本计算
- **reports** - 报告生成与统计分析

### 前端模块
- **auth** - 登录/注册页面
- **dashboard** - 仪表盘与概览
- **products** - 商品管理界面
- **recipes** - 菜谱管理界面
- **locations** - 地点与地图界面
- **reports** - 报告与统计界面

## API 端点

### 认证 API
- `GET /api/v1/auth/config` - 获取注册配置
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `GET /api/v1/auth/me` - 获取当前用户信息

### 核心 API
- `GET/POST /api/v1/products/` - 商品价格记录
- `GET/POST /api/v1/locations/` - 地点管理
- `GET/POST /api/v1/nutrition/` - 营养数据
- `GET/POST /api/v1/recipes/` - 菜谱管理
- `GET/POST /api/v1/reports/` - 报告统计

## 开发规范

### Python 代码规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 Flake8 进行代码检查
- 使用 MyPy 进行类型检查

### JavaScript/TypeScript 代码规范
- 使用 Prettier 进行代码格式化
- 使用 ESLint 进行代码检查
- 遵循 Vue 3 最佳实践

### Git 工作流
- 使用 Conventional Commits 提交规范
- 保持主分支稳定
- 功能开发在特性分支进行
- 通过 Pull Request 进行代码审查

## 部署说明

详见 [DEPLOYMENT.md](DEPLOYMENT.md) 和 [QUICKSTART.md](QUICKSTART.md)

## 环境变量

### 后端
- `DATABASE_URL` - 数据库连接字符串
- `SECRET_KEY` - 应用密钥
- `JWT_SECRET_KEY` - JWT 签名密钥
- `REGISTRATION_REQUIRE_INVITE_CODE` - 是否需要邀请码注册

### 前端
- `VITE_API_URL` - 后端 API 地址（默认为 `/api/v1`）