# 部署

生计是前后端分离 monorepo：后端 FastAPI（uv 管理依赖），前端 Vue 3 + Vite（npm）。**没有 Docker 部署**——直接 uvicorn 跑后端，Nginx 托管前端静态文件并反代。

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

启动：

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

控制台显示 `INFO: Application startup complete.` 即启动成功。

> 首次启动会自动从 GitHub 拉取 HowToCook 数据（菜谱/原料/营养），需联网。不想自动导入就设 `FIRST_RUN_INIT_RECIPES=false`。

## 前端

```bash
cd frontend
npm install

# 开发模式（热重载，端口 5173）
npm run dev

# 生产构建（产物在 dist/）
npm run build
```

开发访问 `http://localhost:5173/`，后端 API 默认 `http://localhost:8000/`。

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

## 生产部署建议

- 前端 `npm run build`，`dist/` 交给 **Nginx** 托管
- 后端 uvicorn（生产建议多 worker，如 `--workers 4`）跑 8000，Nginx 把 `/api` 反代到后端
- 启用 **HTTPS**
- `.env` 里 `DEBUG=false`，改掉 `JWT_SECRET_KEY` 的默认值
- 前端 `.env` 的 `VITE_ALLOWED_HOSTS` 加上你反代的域名

## API 文档

后端启动后自带交互式文档：

- Swagger UI：`http://host:8000/docs`
- ReDoc：`http://host:8000/redoc`

## 下一步

配置项详解和首次启动的行为见 [配置与首次启动](config-init.md)。日常运维见 [升级与备份](upgrade-backup.md)。
