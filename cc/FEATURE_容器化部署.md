# 容器化部署

> 日期：2026-07-08
> 设计稿：[docs/plans/2026-07-08-容器化部署-design.md](../docs/plans/2026-07-08-容器化部署-design.md)

## 概述

为项目提供 Docker 容器化，支持两种部署形态：

- **统一部署**（all-in-one）：前后端 + nginx 同容器，一个端口访问完整应用
- **分开部署**：frontend + backend 独立镜像，便于水平扩展与负载均衡

镜像**开箱即用**（不挂载也能跑，验证基础功能），并提供配置/数据/静态/日志的持久化挂载点。

## 决策摘要

| 项 | 选型 |
|---|---|
| 数据库 | 默认 SQLite，`DATABASE_URL` 走 `.env`（requirements 已含 `psycopg2-binary` + `pymysql`，换库改一行） |
| 统一部署形态 | 单容器 nginx + uvicorn（supervisord 编排） |
| 前端后端地址 | 运行时注入 `BACKEND_URL`（`VITE_API_URL=/api/v1` 相对路径） |
| Agent CLI | 不进镜像（精简；维护任务台仅本机环境用） |
| HTTPS | 容器跑 HTTP，外层终结 TLS |

## 镜像拓扑

一份根 `Dockerfile`，multi-stage 多 target，三 target 共享 frontend-builder/backend 层：

- `frontend-builder`（node:20-alpine）：`npm ci` + `vite build` → dist
- `backend`（python:3.11-slim）：`pip install` + uvicorn，非 root，HEALTHCHECK 打 /health
- `all-in-one`（FROM backend）：+ apt 装 nginx/supervisor/gettext-base + dist + supervisord 编排
- `frontend`（nginx:alpine）：dist + entrypoint envsubst 注入 BACKEND_URL

**stage 顺序**：frontend-builder → backend → all-in-one → frontend。all-in-one 排在 frontend 之前，经典 builder 构 all-in-one 时走到即止，不需拉 nginx:alpine（all-in-one 的 nginx 是 apt 装的）。

## 关键技术点

- **`.env` 用 `env_file` 注入，非 volume 挂载**：避免 volume 挂 `.env` 文件在宿主不存在时被当目录挂载、容器内 `/app/.env` 变目录致 pydantic 报错的坑。`data/static/logs` 才用 bind volume。
- **前端配置分工**：构建期 ARG（`VITE_API_URL` 等，编译进 JS，不变）+ 运行时 envsubst（`BACKEND_URL`，会变）。`VITE_API_URL=/api/v1` 相对路径 → 前端请求走「当前 origin + /api/v1」→ 由 nginx 反代决定真后端 → 前端镜像构建一次到处部署。
- **entrypoint envsubst 限定替换**：`envsubst '${BACKEND_URL}'` 只替换 BACKEND_URL，保留 `$host`/`$uri` 等 nginx 内置变量不被误伤。
- **Windows 编写的 .sh**：Dockerfile 里 `sed -i 's/\r$//'` 去 CRLF，避免容器内 `^M` 报错。
- **supervisord 开 `[unix_http_server]` socket**：`supervisorctl status/restart` 可查控进程。
- **开箱即用兜底链**：Settings 字段默认值 + Dockerfile `mkdir data static logs` + entrypoint BACKEND_URL 默认值。`docker run -p 80:80 livecalc:all-in-one` 即用。
- **all-in-one 进程编排**：uvicorn 绑 `127.0.0.1:8000`（appuser 跑），nginx（root）serve dist + 反代 `/api` 到本地 uvicorn。
- **首启导入**：`FIRST_RUN_INIT_RECIPES` 默认 true，首启从 GitHub clone HowToCook 菜谱（之后跳过）；离线/嫌慢 `.env` 设 false 或用 `DATA_LOCAL_PATH` 挂本地数据。

## 文件清单

**新增**：[Dockerfile](../Dockerfile)、[.dockerignore](../.dockerignore)、[docker-compose.yml](../docker-compose.yml)、[docker-compose.split.yml](../docker-compose.split.yml)、[deploy/nginx/default.conf.template](../deploy/nginx/default.conf.template)、[deploy/supervisord.conf](../deploy/supervisord.conf)、[deploy/frontend-entrypoint.sh](../deploy/frontend-entrypoint.sh)、[deploy/all-in-one-entrypoint.sh](../deploy/all-in-one-entrypoint.sh)

**修改**：[frontend/.env.example](../frontend/.env.example)（补 `BACKEND_URL` 行）

## 验证

- 前端 `npm run build` ✓（36.75s）、后端 `compileall app/` ✓、`docker compose config` ×2 ✓、entrypoint `sh -n` ✓
- `docker build` 三 target ✓：`livecalc:all-in-one` 372MB、`livecalc:backend` 314MB、`livecalc:frontend` 69.6MB
- 点火测试（all-in-one，`FIRST_RUN_INIT_RECIPES=false`，8080 端口临时）：前端 `/` 返回 index.html ✓、`/api/v1/auth/config` 经 nginx 反代返回 JSON ✓、`supervisorctl status` nginx + uvicorn 均 RUNNING ✓

## 已知与遗留

- **生产密钥**：`JWT_SECRET_KEY` 等开箱默认 dev 占位，部署挂 `.env` 必须改。
- **负载均衡**：`backend` 多副本需切 PG（SQLite 单文件多写不支持）。
- **HTTPS**：容器仅 HTTP，TLS 由外层终结；容器内证书（Caddy/certbot）另开一期。
- **既有后端 bug（与容器化无关）**：[main.py:302](../backend/app/main.py#L302) `register_all` 报 `name 'Session' is not defined`，提议审核框架未注册（try/except 兜住不崩），点火测试时暴露，需另行排查。
- **构建网络注意**：Docker Hub 国内不稳，需给 Docker Desktop 配代理或 registry mirror；本地已有基础镜像后用 `DOCKER_BUILDKIT=0 docker build --pull=false` 避免联网核对 manifest（buildkit 与经典 builder 的 FROM 行为差异：buildkit 总联网 load metadata，经典 builder 按序构建所有 stage 直到目标）。
