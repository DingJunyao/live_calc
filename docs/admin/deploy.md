# 部署

生计是前后端分离 monorepo：后端 FastAPI（uv 管理依赖），前端 Vue 3 + Vite（npm）。支持两种部署方式：**Docker 容器化部署**（推荐，开箱即用）和**手动部署**（uvicorn 跑后端 + Nginx 托管前端静态文件并反代）。下面的步骤是手动部署；想用 Docker 直接跳到 [Docker 部署](#docker-部署)。

## 环境要求

- **Python 3.11+**（实测 3.14 可用）
- **Node.js**（推荐 LTS）
- **uv**（后端依赖管理）
- **Git**
- 数据库：SQLite（默认，零配置）/ MySQL / PostgreSQL

## 后端

```bash
# 1. 克隆
git clone <仓库地址>
cd live_calc/backend

# 2. 配置（从示例复制后编辑）
cp .env.example .env
#   至少改：JWT_SECRET_KEY、DATABASE_URL（详见 配置与首次启动）

# 3. 装依赖
uv sync
#   或：pip install -r requirements.txt
```

启动（推荐——地址与端口读 `backend/.env` 的 `APP_HOST` / `APP_PORT`，默认 `0.0.0.0:8000`）：

```bash
uv run python -m app.main
```

也可沿用 uvicorn 直起（端口需命令行指定，不读 `.env`）：

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

控制台显示 `INFO: Application startup complete.` 即启动成功。

> 首次启动会自动从 GitHub 拉取 HowToCook 数据（菜谱/原料/营养），需联网。不想自动导入就设 `FIRST_RUN_INIT_RECIPES=false`。

## 前端

```bash
cd frontend
npm install

# 开发模式（热重载，默认端口 5173，由 .env 的 VITE_DEV_PORT 控制）
npm run dev

# 生产构建（产物在 dist/）
npm run build
```

开发访问 `http://localhost:5173/`（端口由 `frontend/.env` 的 `VITE_DEV_PORT` 控制），后端 API 默认 `http://localhost:8000/`。

> 自定义端口时，前端的 `VITE_DEV_BACKEND_URL` 必须指向后端实际端口（默认 `http://localhost:8000`），否则 dev proxy 打不到后端。改了 `.env` 要重启服务才生效。

然后**立即**注册一个账号，该账号作为创建者和管理员。

## 数据库

默认 SQLite（`backend/data/livecalc.db`，零配置，适合开发）。生产建议 MySQL 或 PostgreSQL：

| 引擎 | `DATABASE_URL` | 驱动 |
|---|---|---|
| SQLite | `sqlite:///./data/livecalc.db` | 内置 |
| MySQL | `mysql+pymysql://user:pwd@host:3306/db?charset=utf8mb4` | PyMySQL |
| PostgreSQL | `postgresql://user:pwd@host:5432/db` | psycopg2 |

切换引擎的步骤：

1. 装对应驱动
2. 改 `DATABASE_URL`
3. 跑 `backend/scripts/sql/` 下对应引擎的脚本初始化/迁移表结构

> 表结构由 SQLAlchemy 的 `create_all` 自动创建（不走 alembic）。表结构变更时，用 `scripts/sql/` 下的迁移脚本——每个变更都提供 SQLite / MySQL / PostgreSQL（含 PostGIS 版本）四套。

## Docker 部署

项目自带容器化部署，开箱即用。根目录提供：

- `Dockerfile`：multi-stage 构建，三个 target——`frontend`（仅前端 + nginx）、`backend`（仅后端）、`all-in-one`（前后端合一，nginx + uvicorn 由 supervisord 编排）
- `docker-compose.yml`：统一部署（单容器 all-in-one）
- `docker-compose.split.yml`：分开部署（前端、后端独立容器，便于横向扩展）
- `deploy/`：nginx 配置模板、supervisord 配置、entrypoint 脚本

快速启动（统一部署，默认 SQLite，映射 80 端口）：

```bash
docker compose up -d --build
# 访问 http://localhost
```

切换数据库改 `backend/.env` 的 `DATABASE_URL`（PG/MySQL 驱动已在镜像内）。生产务必改 `JWT_SECRET_KEY`、设 `DEBUG=false`。前端构建时 `VITE_API_URL` 走相对路径 `/api/v1`，由 nginx 反代后端，部署时不必改。

> Docker 版本未封装 Claude Code（Agent 任务台用到时请自行安装配置）。

## 生产部署建议

- 前端 `npm run build`，`dist/` 交给 **Nginx** 托管
- 后端 uvicorn（生产建议多 worker，如 `--workers 4`，端口见 `.env` 的 `APP_PORT`，默认 8000），Nginx 把 `/api` 反代到后端
- 启用 **HTTPS**
- `.env` 里 `DEBUG=false`，改掉 `JWT_SECRET_KEY` 的默认值
- 前端 `.env` 的 `VITE_ALLOWED_HOSTS` 加上你反代的域名

## API 文档

后端启动后自带交互式文档：

- Swagger UI：`http://host:8000/docs`（端口同 `APP_PORT`）
- ReDoc：`http://host:8000/redoc`

## 下一步

配置项详解和首次启动的行为见 [配置与首次启动](config-init.md)。日常运维见 [升级与备份](upgrade-backup.md)。
