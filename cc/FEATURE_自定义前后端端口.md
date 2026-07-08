# 自定义前后端端口

## 背景
原前后端开发端口均为硬编码：前端 vite `port: 5173` + dev proxy `target: 'http://localhost:8000'`（[vite.config.ts](../frontend/vite.config.ts)）；后端无端口配置项，靠 uvicorn 命令行 `--port` 决定。换端口需改代码或记命令行参数，不便。

## 改动（环境变量驱动，KISS）
前端：
- [vite.config.ts](../frontend/vite.config.ts)：`port` 读 `VITE_DEV_PORT`（默认 5173），proxy `target` 读 `VITE_DEV_BACKEND_URL`（默认 http://localhost:8000）
- [frontend/.env](../frontend/.env) / [.env.example](../frontend/.env.example)：新增 `VITE_DEV_PORT`、`VITE_DEV_BACKEND_URL`

后端：
- [config.py](../backend/app/config.py)：Settings 新增 `app_host`（默认 0.0.0.0）、`app_port`（默认 8000）
- [main.py](../backend/app/main.py)：新增 `if __name__ == "__main__"` 块，`python -m app.main` 启动时读 settings 调 `uvicorn.run`（reload=True）
- [backend/.env](../backend/.env) / [.env.example](../backend/.env.example)：新增 `APP_HOST`、`APP_PORT`

## 自定义端口方法
1. 后端端口：改 `backend/.env` 的 `APP_PORT`
2. 前端端口：改 `frontend/.env` 的 `VITE_DEV_PORT`
3. **同步**：前端 `VITE_DEV_BACKEND_URL` 必须指向后端新 `APP_PORT`（如后端改 8001，这里也改 `http://localhost:8001`）——这是前后端联通的命脉
4. 重启前后端服务（env 仅启动时读取）

## 后端启动命令
推荐 `uv run python -m app.main`（在 backend 目录，端口自动读 APP_PORT）。
原 `uvicorn app.main:app --reload` 仍可用，但端口需手动 `--port`。

## 验证
前端 `npm run build` 通过（✓ built in 23.38s）；后端 `py_compile`（config.py + main.py）通过。无表结构变更，无需 alembic/SQL。

## 备注
- 后端 CORS 全开（`allow_origins=["*"]`，[main.py](../backend/app/main.py) CORSMiddleware），改端口无需同步白名单。
- 前端 `src/` 零硬编码后端地址，全走 `VITE_API_URL=/api/v1` 相对路径经 vite proxy，业务代码无需改动。
- 生产环境前后端分离部署（不走 vite proxy）时，需把 `VITE_API_URL` 改为后端完整地址。
