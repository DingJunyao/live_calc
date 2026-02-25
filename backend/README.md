# Backend API

生计项目的后端 API,基于 FastAPI。

## 快速开始

```bash
# 安装依赖
poetry install

# 配置环境变量
cp .env.example .env

# 初始化数据库
poetry run alembic upgrade head

# 启动服务
poetry run uvicorn app.main:app --reload
```

## API 文档

启动后访问 http://localhost:8000/docs 查看 API 文档。
