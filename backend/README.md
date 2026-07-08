# Backend API

生计的后端服务，基于 FastAPI。完整的安装、配置、部署说明见 [文档 · 部署](../docs/admin/deploy.md)。

## 快速启动

```bash
cp .env.example .env   # 编辑配置，详见 ../docs/admin/config-init.md
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

> 依赖用 **uv** 管理（不是 Poetry / alembic）。建表走 `create_all`，表结构变更用 `scripts/sql/` 下的脚本。详见 [部署](../docs/admin/deploy.md)。
