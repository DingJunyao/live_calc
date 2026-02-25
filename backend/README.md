# Backend API

生计项目的后端 API,基于 FastAPI。

## 环境要求

- Python 3.11 或更高版本
- Poetry (依赖管理工具)

## 快速开始

### 1. 安装 Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. 安装依赖

```bash
poetry install
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件,设置必要的配置项
```

### 4. 初始化数据库

```bash
poetry run alembic upgrade head
```

### 5. 启动服务

```bash
poetry run uvicorn app.main:app --reload
```

## API 使用示例

### 获取 API 文档

启动后访问 http://localhost:8000/docs 查看 Swagger 文档。

### 基本请求示例

```bash
# 健康检查
curl http://localhost:8000/health

# 获取商品列表
curl http://localhost:8000/api/v1/products

# 创建商品记录 (需要认证)
curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "大米", "price": 5.5, "unit": "kg", "location_id": 1}'
```
