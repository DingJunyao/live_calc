# 生计 - 后端模块 (FastAPI)

## 概述

后端模块是一个基于 FastAPI 的 REST API 服务，负责处理业务逻辑、数据库操作和用户认证等功能。

## 目录结构

```
backend/
├── app/
│   ├── api/           # API 路由定义
│   │   ├── auth.py    # 认证相关端点
│   │   ├── products.py # 产品价格记录
│   │   ├── locations.py # 地点管理
│   │   ├── nutrition.py # 营养数据库
│   │   ├── recipes.py  # 菜谱管理
│   │   └── reports.py  # 报告统计
│   ├── core/          # 核心配置与安全
│   │   ├── database.py # 数据库配置
│   │   ├── security.py # 安全相关函数
│   │   └── config.py   # 应用配置
│   ├── models/        # 数据库模型
│   │   ├── user.py    # 用户模型
│   │   ├── product.py # 产品模型
│   │   ├── location.py # 地点模型
│   │   ├── nutrition.py # 营养模型
│   │   ├── recipe.py   # 菜谱模型
│   │   └── expense.py  # 支出模型
│   ├── schemas/       # Pydantic 数据模式
│   │   ├── auth.py    # 认证相关模式
│   │   ├── product.py # 产品相关模式
│   │   ├── location.py # 地点相关模式
│   │   ├── nutrition.py # 营养相关模式
│   │   ├── recipe.py   # 菜谱相关模式
│   │   └── report.py   # 报告相关模式
│   └── utils/         # 工具函数
│       └── unit_converter.py # 单位转换工具
├── alembic/           # 数据库迁移脚本
├── data/              # 数据存储目录
└── tests/             # 测试用例
```

## 核心功能模块

### 认证模块 (auth)
- 用户注册与登录
- JWT 令牌管理（访问令牌和刷新令牌）
- 用户信息获取
- 邀请码验证

### 产品价格模块 (products)
- 商品价格记录的增删改查
- 历史价格查询
- 多单位支持（重量、体积等）
- 地点关联记录

### 地点管理模块 (locations)
- 地点的增删改查
- 地图服务集成
- 路线规划与距离计算
- 收藏地点管理

### 营养数据库模块 (nutrition)
- USDA 营养数据集成
- 智能配料匹配算法
- 营养数据校正机制
- 模糊搜索功能

### 菜谱管理模块 (recipes)
- 菜谱的创建与编辑
- 菜谱成本计算
- 营养成分分析
- 菜谱分类与标签

### 报告统计模块 (reports)
- 支出报告生成
- 价格趋势分析
- 数据可视化

## 技术实现

### 数据库模型关系
- `User` ↔ `ProductRecord` (一对多)
- `User` ↔ `Location` (一对多)
- `User` ↔ `FavoriteLocation` (一对多)
- `User` ↔ `Recipe` (一对多)
- `Ingredient` ↔ `NutritionData` (多对一)

### 安全措施
- 密码哈希（SHA256 前端 + bcrypt 后端双重加密）
- JWT 令牌验证
- 输入验证与过滤
- SQL 注入防护

### 性能优化
- 数据库索引优化
- 连接池管理
- 缓存策略（待实现）
- 异步处理（待实现）

## API 端点详情

### 认证端点
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `GET /api/v1/auth/me` - 获取用户信息
- `GET /api/v1/auth/config` - 获取配置

### 产品端点
- `POST /api/v1/products/` - 创建产品记录
- `GET /api/v1/products/` - 查询产品记录
- `GET /api/v1/products/{id}` - 获取特定产品记录
- `GET /api/v1/products/history/{name}` - 查询产品历史价格

### 地点端点
- `POST /api/v1/locations/` - 创建地点
- `GET /api/v1/locations/` - 查询地点
- `POST /api/v1/locations/route` - 计算路线
- `GET /api/v1/locations/favorites/` - 获取收藏地点

### 营养端点
- `GET /api/v1/nutrition/search` - 搜索营养数据
- `POST /api/v1/nutrition/match` - 匹配配料
- `POST /api/v1/nutrition/correct` - 校正匹配结果

### 菜谱端点
- `POST /api/v1/recipes/` - 创建菜谱
- `GET /api/v1/recipes/` - 查询菜谱
- `GET /api/v1/recipes/{id}/cost` - 计算菜谱成本
- `GET /api/v1/recipes/{id}/nutrition` - 获取菜谱营养信息

### 报告端点
- `POST /api/v1/reports/expenses/` - 创建支出记录
- `GET /api/v1/reports/expense` - 生成支出报告
- `GET /api/v1/reports/price-trend` - 获取价格趋势

## 配置项

### 环境变量
- `DATABASE_URL` - 数据库连接 URL
- `SECRET_KEY` - 应用密钥
- `JWT_SECRET_KEY` - JWT 令牌密钥
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - 访问令牌过期时间
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - 刷新令牌过期时间
- `REGISTRATION_REQUIRE_INVITE_CODE` - 注册是否需要邀请码
- `DEFAULT_MAP_PROVIDER` - 默认地图提供商
- `TASK_SCHEDULER_TYPE` - 任务调度器类型

## 开发规范

### Python 代码规范
- 使用 Black 进行代码格式化（line length = 88）
- 使用 isort 进行导入排序
- 使用 Flake8 进行代码质量检查
- 使用 MyPy 进行类型检查
- 文档字符串遵循 Google 风格

### API 设计原则
- RESTful API 设计
- 统一的错误响应格式
- 输入验证使用 Pydantic
- 响应数据使用序列化模式

### 安全考虑
- 所有密码必须哈希存储
- JWT 令牌需验证类型和有效期
- 所有输入需验证和清理
- 敏感数据加密传输