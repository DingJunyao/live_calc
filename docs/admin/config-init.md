# 配置与首次启动

这篇逐项讲清前后端的环境变量，以及首次启动时数据导入的行为。

## 前端 `frontend/.env`

```conf
VITE_API_URL=/api/v1
# 允许的域名。做反代时加上准备反代的域名
VITE_ALLOWED_HOSTS=example,localhost,127.0.0.1,::1
# 开发服务器端口与后端地址（vite.config.ts 读取；改后端端口时 VITE_DEV_BACKEND_URL 要同步）
VITE_DEV_PORT=5173
VITE_DEV_BACKEND_URL=http://localhost:8000
# 数据仓库图片回退地址（本地图片不存在时用远程地址）
VITE_DATA_REPO_IMAGE_BASE=https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out
# 请求超时（毫秒）
VITE_REQUEST_TIMEOUT=10000        # 默认请求超时
VITE_LONG_REQUEST_TIMEOUT=30000   # 长任务超时（成本计算、全部历史等）
```

## 后端 `backend/.env`

```conf
# 数据库（见 部署 的引擎表）
DATABASE_URL=sqlite:///./data/livecalc.db

# 应用
DEBUG=true
# 开发服务器监听地址与端口（`python -m app.main` 启动时生效）
APP_HOST=0.0.0.0
APP_PORT=8000

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080  # access token 有效期（分钟），默认 7 天
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 日志
LOG_LEVEL=INFO
LOG_DIR=./logs

# 首次启动配置
FIRST_RUN_INIT_RECIPES=true

# 数据仓库（导入菜谱/原料/营养的来源）
DATA_REPO_URL=https://github.com/DingJunyao/HowToCook_json.git
DATA_REPO_BRANCH=main
DATA_REPO_DIR=out
# 从本地仓库导入时设置（替代远程拉取）
# DATA_LOCAL_PATH=./data/import

# USDA FoodData Central 下载
USDA_HTTP_PROXY=
USDA_DOWNLOAD_TIMEOUT=600
USDA_CONNECT_TIMEOUT=8
USDA_DOWNLOAD_RETRIES=20
USDA_DOWNLOAD_CONCURRENCY=5

# Agent 任务超时
AGENT_IDLE_TIMEOUT=120
AGENT_TOTAL_TIMEOUT=600
AGENT_APPROVAL_TIMEOUT=3600

# 导入超时
IMPORT_DOWNLOAD_TIMEOUT=300
```

> 生产环境务必改掉 `JWT_SECRET_KEY` 的默认值，并设 `DEBUG=false`。

## 首次启动的数据导入

后端首次启动时（数据库为空），会自动导入一批初始数据：

- **来源**：默认从 `DATA_REPO_URL`（HowToCook_json 仓库）拉取；若设了 `DATA_LOCAL_PATH` 则从本地目录读
- **内容**：菜谱、原料、营养数据（HowToCook 兼容格式）
- **触发条件**：仅**首次初始化**时执行。判断依据是"是否已有 `source=json_repo` 的菜谱"——有则跳过，避免每次重启重复导入
- **关闭**：`FIRST_RUN_INIT_RECIPES=false` 则不自动导入（之后可在 [数据维护中心](data-maintenance.md) 手动触发）

> 这意味着：第一次启动需联网（拉远程仓库）；后续重启不会重复导入。如果你想换数据源或重新导入，在数据维护中心操作。

## 邀请码注册

是否需要邀请码由管理员在后台「邀请码管理」页面开关控制（存 `system_config` 表，见 [后台管理 · 邀请码管理](admin-pages.md#邀请码管理)），**不是环境变量**。开启时新用户注册必须填邀请码，关闭则开放注册。

## 下一步

装好之后，日常运维看 [升级与备份](upgrade-backup.md)。后台管理功能看 [后台管理](./) 各篇。
