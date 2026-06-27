# 配置

## 前端 `.env` 文件

```conf
VITE_API_URL=/api/v1
# 允许的域名。如果你要做反代，则添加上准备反代的域名。
VITE_ALLOWED_HOSTS=example,localhost,127.0.0.1,::1

# 数据仓库图片回退地址（当本地图片不存在时使用远程地址）
VITE_DATA_REPO_IMAGE_BASE=https://raw.githubusercontent.com/DingJunyao/HowToCook_json/corr/out

# 请求超时配置（毫秒）
VITE_REQUEST_TIMEOUT=10000       # 默认请求超时
VITE_LONG_REQUEST_TIMEOUT=30000  # 长任务请求超时（成本计算、全部历史等）
```

## 后端 `.env` 文件

```conf
# 数据库配置
# 可选引擎（需安装对应驱动，见 requirements.txt）：
#   SQLite（开发）: sqlite:///./data/livecalc.db
#   MySQL:         mysql+pymysql://user:password@host:3306/dbname?charset=utf8mb4
#   PostgreSQL:    postgresql://user:password@host:5432/dbname
# 切换引擎后需执行对应 SQL 脚本初始化表结构（见 scripts/sql/ 目录）
DATABASE_URL=sqlite:///./data/livecalc.db

# 应用配置
DEBUG=true

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=./logs

# 首次启动配置
FIRST_RUN_INIT_RECIPES=true

# 数据仓库配置（用于导入菜谱、原料、营养数据）
DATA_REPO_URL=https://github.com/DingJunyao/HowToCook_json.git
# 如果从本地仓库导入，则设置
DATA_LOCAL_PATH=./data/import
DATA_REPO_BRANCH=main
DATA_REPO_DIR=out

# USDA FoodData Central 下载配置
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
