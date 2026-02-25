# 生计 - 生活成本计算器

> 记录商品价格，计算烹饪成本，优化生活开支

## 功能特性

- 📝 商品价格记录 - 记录不同时间、不同地点的商品价格
- 🍳 菜谱成本计算 - 根据价格记录计算菜谱成本
- 🥗 营养成分分析 - 基于 USDA 数据库的营养分析
- 📍 地图与路线规划 - 集成地图服务，计算出行成本
- 📊 生活成本报告 - 生成每日、每周、每月报告
- 💰 多币种支持 - 支持多种货币
- 🌏 多单位转换 - 支持公制/市制/英制转换
- 🔐 用户认证 - 支持 JWT 认证和邀请码注册

## 快速开始

### Docker 部署（推荐）

```bash
# 克隆代码
git clone https://github.com/your-repo/live_calc.git
cd live_calc

# 复制环境变量配置
cp backend/.env.example backend/.env

# 启动服务
docker-compose up -d

# 访问应用
# 前端: http://localhost
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 本地开发

#### 后端

```bash
cd backend

# 安装依赖
poetry install

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 初始化数据库
poetry run alembic upgrade head

# 启动开发服务器
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量（可选）
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 技术栈

### 后端
- **框架**: FastAPI - 现代化的 Python Web 框架
- **ORM**: SQLAlchemy - Python SQL 工具包和对象关系映射
- **迁移**: Alembic - 数据库迁移工具
- **认证**: Python-JOSE + Passlib - JWT 认证和密码哈希
- **任务调度**: APScheduler - 任务调度器
- **异步任务**: Celery（可选）- 分布式任务队列

### 前端
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

## 项目结构

```
live_calc/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心配置
│   │   ├── models/        # 数据库模型
│   │   ├── schemas/       # Pydantic 模式
│   │   ├── services/      # 业务逻辑
│   │   └── utils/         # 工具函数
│   ├── alembic/           # 数据库迁移
│   └── tests/             # 测试
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── api/          # API 客户端
│   │   ├── components/   # 组件
│   │   ├── stores/       # Pinia stores
│   │   ├── views/        # 页面视图
│   │   └── router/       # 路由配置
│   └── public/           # 静态资源
├── docker-compose.yml     # Docker Compose 配置
└── README.md             # 项目说明
```

## API 文档

启动后端服务后，访问以下地址查看完整的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 环境变量

### 后端环境变量（backend/.env）

```bash
# 数据库
DATABASE_URL=sqlite:///./data/livecalc.db

# 安全配置
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# 注册配置
REGISTRATION_REQUIRE_INVITE_CODE=false

# 地图服务（可选）
AMAP_API_KEY=
BAIDU_API_KEY=
TENCENT_API_KEY=
TIANDITU_API_KEY=

# 营养数据库
USDA_API_KEY=
```

### 前端环境变量（frontend/.env）

```bash
# API 地址
VITE_API_URL=http://localhost:8000/api/v1
```

## 开发指南

### 运行测试

```bash
# 后端测试
cd backend
poetry run pytest

# 前端测试
cd frontend
npm run test
```

### 代码格式化

```bash
# 后端
cd backend
poetry run black .
poetry run isort .

# 前端
cd frontend
npm run lint
npm run format
```

### 数据库迁移

```bash
# 创建迁移
poetry run alembic revision --autogenerate -m "description"

# 执行迁移
poetry run alembic upgrade head

# 回滚迁移
poetry run alembic downgrade -1
```

## 部署

详细的部署指南请参考 [DEPLOYMENT.md](DEPLOYMENT.md)

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献流程。

## 许可证

[MIT License](LICENSE)

## 联系方式

- 项目主页: https://github.com/your-repo/live_calc
- 问题反馈: https://github.com/your-repo/live_calc/issues

## 致谢

- 菜谱参考: [HowToCook](https://github.com/Anduin2017/HowToCook)
- 营养数据: [USDA FoodData Central](https://fdc.nal.usda.gov/)
