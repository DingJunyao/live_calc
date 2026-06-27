# 运行

## 运行前准备

确保已安装 Python 和 Node.js。

### 依赖

前端依赖的安装以 `npm` 为例：

```bash
cd frontend
npm install
```

后端依赖的安装以 `pip` 为例：

```bash
cd backend
pip install -r requirements.txt
```

### 配置文件

如果你刚拉取代码，则复制 `frontend/.env.example` 到 `frontend/.env`，`backend/.env.example` 到 `backend/.env`，并修改里面的内容。

对于绝大多数情况来说，需要关注以下部分：

#### 前端

```conf
# 允许的域名。如果你要做反代，则添加上准备反代的域名。
VITE_ALLOWED_HOSTS=example,localhost,127.0.0.1,::1
```

#### 后端

```conf
# 数据库配置
# 可选引擎（需安装对应驱动，见 requirements.txt）：
#   SQLite（开发）: sqlite:///./data/livecalc.db
#   MySQL:         mysql+pymysql://user:password@host:3306/dbname?charset=utf8mb4
#   PostgreSQL:    postgresql://user:password@host:5432/dbname
# 切换引擎后需执行对应 SQL 脚本初始化表结构（见 scripts/sql/ 目录）
DATABASE_URL=sqlite:///./data/livecalc.db

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
```

## 启动

启动后端服务：

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

当控制台显示 `INFO:     Application startup complete.` 时，表示后端服务启动成功。

启动前端服务：

```bash
cd frontend
npm run dev
```

访问应用：

- 前端: http://localhost:5173/
- 后端 API: http://localhost:8000/

访问 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 初次启动

默认情况下，后端初次启动时，会自动从 GitHub 仓库导入来自于 `https://github.com/DingJunyao/HowToCook_json` 的菜谱、原料、营养数据。请确保网络连接正常。

如果你不想自动导入，可在运行后端前，修改 `backend/.env` 文件，将 `FIRST_RUN_INIT_RECIPES` 设置为 `false`。
