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
cd livecalc/backend

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

项目自带容器化部署，开箱即用。

### 从镜像仓库拉取

镜像已上传至 GHCR 与 Docker Hub，覆盖 amd64 和 arm64 架构，可拉取。

下面以 Docker Hub 上的 aio（All in One，包括前端和后端，默认用 SQLite 存储，不包括 Claude Code 和 Codex）镜像为例，如果有其他需求可以查看仓库的 `docker-compose.example.yml` 和 `docker-compose.split.yml`。

先在某个目录（工作目录）下建立好以下目录并赋予正确权限：

- `backend`
- `data`
- `static`
- `logs`

然后复制仓库的 `backend/.env.example` 文件，并改名为 `.env`，填入对应内容。

#### 使用 Docker 命令

```bash
docker pull dingjunyao/livecalc:latest
docker run -d -p "前端端口:80" \
    -v "./data:/app/data" \
    -v "./static:/app/static" \
    -v "./logs:/app/logs" \
    --env-file ./.env \
    dingjunyao/livecalc:latest
```

> `aio` 为默认的配置，`latest`、`vX.X.X` 等未注明类别的镜像均为对应版本的 `aio`。镜像标签的含义，见下面的 [自动发布镜像](#自动发布镜像github-actions) 章节。

#### 使用 Docker Compose

工作目录下创建 `docker-compose.yml` ，配置文件如下：

```yaml
services:
  livecalc:
    image: dingjunyao/livecalc:latest
    container_name: livecalc
    ports:
      - "前端端口:80"
    env_file:
      - ./.env
    volumes:
      - ./data:/app/data
      - ./static:/app/static
      - ./logs:/app/logs
    restart: unless-stopped
```

运行：

```bash
docker compose up -d
```

运行后即可在指定的前端端口访问。

### 通过本仓库构建、运行

根目录提供：

- `Dockerfile`：multi-stage 构建，四个 target——`all-in-one`（默认，前后端合一，nginx + uvicorn 由 supervisord 编排）、`frontend`（仅前端 + nginx）、`backend`（仅后端）、`local`（纯前端本地模式，数据存浏览器 IndexedDB）
- `docker-compose.example.yml`：统一部署（单容器 All in One。考虑到可能要自定义，故请自行复制此文件，并改名成 `docker-compose.yml`，然后编辑）
- `docker-compose.split.yml`：分开部署（前端、后端独立容器，便于横向扩展）
- `deploy/`：nginx 配置模板、supervisord 配置、entrypoint 脚本

快速启动（统一部署，默认 SQLite，映射 80 端口）：

```bash
docker compose up -d --build
# 访问 http://localhost
```

切换数据库改 `backend/.env` 的 `DATABASE_URL`（PG/MySQL 驱动已在镜像内）。生产务必改 `JWT_SECRET_KEY`、设 `DEBUG=false`。前端构建时 `VITE_API_URL` 走相对路径 `/api/v1`，由 nginx 反代后端，部署时不必改。

> Docker 版本未封装 Claude Code、Codex（Agent 任务台用到时请自行安装配置）。

### 自动发布镜像（GitHub Actions）

`.github/workflows/docker-publish.yml` 会在 **release 发布**时自动构建并推送 Docker 镜像；也可以在仓库 Actions 页面手动触发（默认构建 `aio`，选 `all` 全量重发，可填版本号）。

**四个类别**共用**同一个镜像名**，靠标签区分：

- **aio**（all-in-one）：前后端合一，nginx + uvicorn 同容器
- **frontend**：仅前端 + nginx（分开部署用）
- **backend**：仅后端 uvicorn（分开部署用）
- **local**：纯前端本地模式（数据存浏览器 IndexedDB，无后端）

- **架构**：`linux/amd64` + `linux/arm64` 双架构
- **镜像名**：
  - GHCR：`ghcr.io/<GitHub 用户名>/<仓库>`，如 `ghcr.io/dingjunyao/livecalc`
  - Docker Hub：`docker.io/<用户名/组织>/<仓库>`，如 `docker.io/dingjunyao/livecalc`

**标签规则**（以版本 `v0.1.0` 为例）：

| 类别 | 标签 |
| --- | --- |
| aio | `v0.1.0-aio`, `v0.1.0`, `latest-aio`, `aio`, `latest` |
| frontend | `v0.1.0-frontend`, `latest-frontend`, `frontend` |
| backend | `v0.1.0-backend`, `latest-backend`, `backend` |
| local | `v0.1.0-local`, `latest-local`, `local` |

手动触发不填版本号时只推滚动标签（`latest-*` / 短名 / `latest`）。

#### GHCR（默认，无需配置）

GHCR 使用 `GITHUB_TOKEN` 自动登录，release 发布后镜像即出现在仓库 **Packages** 页，无需额外配置即可拉取。

#### Docker Hub（可选，配置后同时推送）

在仓库 **Settings → Secrets and variables → Actions** 中配置以下内容：

| 类型 | 名称 | 说明 |
| --- | --- | --- |
| Secret | `DOCKERHUB_USERNAME` | Docker Hub 用户名。与 `DOCKERHUB_TOKEN` 同时设置才会启用 Docker Hub 推送 |
| Secret | `DOCKERHUB_TOKEN` | Docker Hub 访问令牌（Account Settings → Security → Access Tokens 生成，推荐使用令牌而非密码） |
| Variable（可选） | `DOCKERHUB_NAMESPACE` | 镜像命名空间（用户名/组织），默认取 `DOCKERHUB_USERNAME` |
| Variable（可选） | `DOCKERHUB_REPO` | Docker Hub 仓库名，默认取 GitHub 仓库名（小写） |

配置后，下次 release 发布或手动触发会**同时推送到 GHCR 和 Docker Hub**；未配置则只推 GHCR。只需在 Docker Hub 创建一个仓库（如 `livecalc`），所有标签自动推到该仓库下。

拉取示例：

```bash
# aio（默认，最常用）
docker pull dingjunyao/livecalc:latest
docker pull dingjunyao/livecalc:aio

# 分开部署
docker pull dingjunyao/livecalc:frontend
docker pull dingjunyao/livecalc:backend

# 本地模式
docker pull dingjunyao/livecalc:local

# 指定版本
docker pull dingjunyao/livecalc:v0.1.0
docker pull dingjunyao/livecalc:v0.1.0-frontend
```

## 生产部署建议

- 前端 `npm run build`，`dist/` 交给 **Nginx** 托管
- 后端 uvicorn（生产建议多 worker，如 `--workers 4`，端口见 `.env` 的 `APP_PORT`，默认 8000），Nginx 把 `/api` 反代到后端
- 启用 **HTTPS**
- `.env` 里 `DEBUG=false`，改掉 `JWT_SECRET_KEY` 的默认值
- 前端 `.env` 的 `VITE_ALLOWED_HOSTS` 加上你反代的域名

## PWA / HTTPS 部署

前端已适配 PWA，可安装到桌面与移动端主屏。PWA 生效需注意以下几点。

### 1. 必须 HTTPS

service worker 仅在**安全上下文**下注册。开发环境 `localhost` 视为安全上下文，可直接测试安装；**生产环境必须 HTTPS**。

- Caddy 自动 TLS（最省事）：Caddyfile 配域名，Caddy 自动申请 Let's Encrypt 证书
- Nginx + Let's Encrypt：用 certbot 申请证书，Nginx 监听 443 并启用 ssl，80 跳转 443

Docker 部署如需 HTTPS，在容器外（宿主机或前置反代）终止 TLS，或自行改 nginx 模板加证书。

### 2. service worker / manifest 不可长缓存

`sw.js` 与 `manifest.webmanifest` 必须设为不缓存，否则浏览器死缓存旧 SW，新版本更新机制失效——用户拿不到新版本，也弹不出更新提示。Docker 部署的 nginx 模板（`deploy/nginx/default.conf.template`）已内置以下配置；手动 Nginx 部署需自行添加：

```nginx
location = /sw.js {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    expires off;
}
location = /manifest.webmanifest {
    add_header Cache-Control "no-cache";
    expires off;
}
```

> 这两个 `location =`（精确匹配）要排在 `*.js` 的正则长缓存规则之前——精确匹配优先级更高，能盖过 `sw.js` 被 `.js` 规则误长缓存。

### 3. 静态资源长缓存不变

带 hash 的 JS/CSS/图标仍走现有 30 天 immutable 长缓存规则，无需调整。`workbox-<hash>.js`、`pwa-*.png`、`assets/index-<hash>.js` 等都带 hash，长缓存安全。

### 4. 验收

部署后用 Chrome / Edge DevTools → Lighthouse → 仅勾选 PWA 类别 → 生成报告，确认 **Installable**（可安装）通过。

## API 文档

后端启动后自带交互式文档：

- Swagger UI：`http://host:8000/docs`（端口同 `APP_PORT`）
- ReDoc：`http://host:8000/redoc`

## 下一步

配置项详解和首次启动的行为见 [配置与首次启动](config-init.md)。日常运维见 [升级与备份](upgrade-backup.md)。
