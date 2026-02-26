# 生计 - 生活成本计算器 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个全栈生活成本计算器，支持商品价格记录、菜谱成本计算、营养分析、地图集成和报告统计。

**Architecture:** Python 全栈单体应用（FastAPI + Vue 3），支持 Docker 和直接代码部署，内置任务调度器 + 可选 Celery 支持，多数据库兼容（SQLite/MySQL/PostgreSQL）。

**Tech Stack:**
- 后端: FastAPI, SQLAlchemy, Alembic, APScheduler, Celery (可选)
- 前端: Vue 3, Vite, Pinia, Vue Router, Leaflet
- 数据库: SQLite (开发), PostgreSQL/MySQL (生产)
- 容器: Docker, Docker Compose

---

## 阶段 0: 项目初始化

### Task 1: 初始化后端项目结构

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/README.md`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`

**Step 1: 创建 pyproject.toml**

```toml
[tool.poetry]
name = "live-calc"
version = "0.1.0"
description = "生计 - 生活成本计算器"
authors = ["Your Name <you@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.25"
alembic = "^1.13.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"
apscheduler = "^3.10.4"
celery = {extras = ["redis"], version = "^5.3.6", optional = true}
redis = {extras = ["hiredis"], version = "^5.0.1", optional = true}
httpx = "^0.26.0"
aiohttp = "^3.9.1"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
pytest-cov = "^4.1.0"
black = "^24.1.1"
isort = "^5.13.2"
flake8 = "^7.0.0"
mypy = "^1.8.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**Step 2: 创建 .gitignore**

```gitignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.dmypy.json
dmypy.json
.env
.venv
*.log
data/
logs/
```

**Step 3: 创建 .env.example**

```bash
# 数据库配置
DATABASE_URL=sqlite:///./data/livecalc.db

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# 应用配置
APP_NAME=生计
APP_URL=http://localhost:8000
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=true

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 注册配置
REGISTRATION_REQUIRE_INVITE_CODE=false

# 地图服务配置
DEFAULT_MAP_PROVIDER=amap
AMAP_API_KEY=
BAIDU_API_KEY=
TENCENT_API_KEY=

# 任务调度配置
TASK_SCHEDULER_TYPE=apscheduler

# 文件上传配置
MAX_UPLOAD_SIZE=10485760
UPLOAD_DIR=./data/uploads

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=./logs

# 首次启动配置
FIRST_RUN_INIT_RECIPES=true
RECIPES_SOURCE_REPO=https://github.com/Anduin2017/HowToCook
```

**Step 4: Commit**

```bash
cd backend
git add pyproject.toml .env.example .gitignore README.md
git commit -m "chore: initialize backend project structure"
```

---

### Task 2: 初始化前端项目结构

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/.gitignore`

**Step 1: 创建 package.json**

```json
{
  "name": "live-calc-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs --fix --ignore-path .gitignore",
    "format": "prettier --write src/"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.5",
    "pinia": "^2.1.7",
    "axios": "^1.6.5",
    "leaflet": "^1.9.4",
    "@vueuse/core": "^10.7.2",
    "chart.js": "^4.4.1",
    "vue-chartjs": "^5.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.3",
    "@vue/test-utils": "^2.4.3",
    "vite": "^5.0.11",
    "vite-plugin-pwa": "^0.17.4",
    "vitest": "^1.2.1",
    "eslint": "^8.56.0",
    "eslint-plugin-vue": "^9.19.2",
    "prettier": "^3.2.4",
    "typescript": "^5.3.3",
    "@types/node": "^20.11.5",
    "@types/leaflet": "^1.9.8"
  }
}
```

**Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.png'],
      manifest: {
        name: '生计 - 生活成本计算器',
        short_name: '生计',
        description: '记录商品价格，计算烹饪成本，优化生活开支',
        theme_color: '#42b883',
        icons: [
          {
            src: 'icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

**Step 3: 创建 .gitignore**

```gitignore
# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*

node_modules
dist
dist-ssr
*.local

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# Test coverage
coverage
```

**Step 4: Commit**

```bash
cd frontend
git add package.json vite.config.ts tsconfig.json .gitignore
git commit -m "chore: initialize frontend project structure"
```

---

### Task 3: 初始化 Docker 配置

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `nginx.conf`

**Step 1: 创建 Dockerfile**

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Copy dependency files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

# Copy application code
COPY backend/ .

# Create necessary directories
RUN mkdir -p data logs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: live_calc_backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://livecalc:${DB_PASSWORD:-changeme}@db:5432/livecalc
      - REDIS_URL=redis://redis:6379/0
      - APP_URL=http://localhost:8000
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-change-me-in-production}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend/data:/app/data
      - ./backend/logs:/app/logs

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: live_calc_frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro

  db:
    image: postgres:15-alpine
    container_name: live_calc_db
    environment:
      - POSTGRES_USER=livecalc
      - POSTGRES_PASSWORD=${DB_PASSWORD:-changeme}
      - POSTGRES_DB=livecalc
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U livecalc"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: live_calc_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: live_calc_celery
    command: celery -A app.worker worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://livecalc:${DB_PASSWORD:-changeme}@db:5432/livecalc
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - backend
      - redis

volumes:
  postgres_data:
  redis_data:
```

**Step 3: 创建 nginx.conf**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 30d;
        }

        # API 代理
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 前端 SPA
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }
    }
}
```

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml nginx.conf
git commit -m "chore: add docker configuration"
```

---

## 阶段 1: 后端基础架构

### Task 4: 创建后端目录结构和配置

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/api/__init__.py`

**Step 1: 创建 app/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "sqlite:///./data/livecalc.db"

    # Redis 配置
    redis_url: Optional[str] = None

    # 应用配置
    app_name: str = "生计"
    app_url: str = "http://localhost:8000"
    secret_key: str = "your-secret-key-here"
    debug: bool = True

    # JWT 配置
    jwt_secret_key: str = "your-jwt-secret-key"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # 注册配置
    registration_require_invite_code: bool = False
    invite_code_length: int = 8

    # 地图服务配置
    default_map_provider: str = "amap"
    amap_api_key: Optional[str] = None
    baidu_api_key: Optional[str] = None
    tencent_api_key: Optional[str] = None

    # 任务调度配置
    task_scheduler_type: str = "apscheduler"  # apscheduler, celery
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    # 文件上传配置
    max_upload_size: int = 10485760  # 10MB
    upload_dir: str = "./data/uploads"

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # 首次启动配置
    first_run_init_recipes: bool = True
    recipes_source_repo: str = "https://github.com/Anduin2017/HowToCook"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

**Step 2: 创建 app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
import logging
import os

# 配置日志
os.makedirs(settings.log_dir, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{settings.log_dir}/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="生活成本计算器 API",
    version="0.1.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.upload_dir), name="static")

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


# API 路由将在后续任务中添加
# from app.api import auth, products, recipes, ...
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
```

**Step 3: 创建目录结构**

```bash
cd backend
mkdir -p app/{models,schemas,api,services,core,utils} tests
touch app/__init__.py app/models/__init__.py app/schemas/__init__.py app/api/__init__.py
touch app/services/__init__.py app/core/__init__.py app/utils/__init__.py
touch tests/__init__.py
```

**Step 4: Commit**

```bash
cd backend
git add app/
git commit -m "chore: create backend directory structure and configuration"
```

---

### Task 5: 设置数据库和模型

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/user.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

**Step 1: 创建 database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# 创建引擎
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 2: 创建用户模型**

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Step 3: 创建 Alembic 配置**

```bash
cd backend
poetry run alembic init alembic
```

**Step 4: 修改 alembic/env.py**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.core.database import Base

# 导入所有模型
from app.models import user  # noqa: F401

# Alembic 配置
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 5: Commit**

```bash
cd backend
git add app/core/database.py app/models/user.py alembic.ini alembic/
git commit -m "feat: setup database and user model"
```

---

### Task 6: 实现认证和授权

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/tests/test_auth.py`

**Step 1: 创建 security.py**

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
```

**Step 2: 创建 auth.py schemas**

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    password_hash: str  # 前端已 SHA256 加密
    invite_code: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password_hash: str  # 前端已 SHA256 加密


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str]
    is_admin: bool
    email_verified: bool

    class Config:
        from_attributes = True
```

**Step 3: 创建 auth.py API**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash
)
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 检查邀请码（如需要）
    from app.config import settings
    if settings.registration_require_invite_code:
        # TODO: 验证邀请码
        pass

    # 创建用户
    is_first_user = db.query(User).count() == 0
    user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password_hash),
        is_admin=is_first_user
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    # 查找用户
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码（前端已 SHA256，这里再 bcrypt）
    from app.core.security import verify_password
    if not verify_password(user_data.password_hash, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPBearer = Depends(security),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user
```

**Step 4: 创建测试文件**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "test_password_hash"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login():
    # 先注册
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser2",
            "email": "test2@example.com",
            "password_hash": "test_password_hash"
        }
    )

    # 再登录
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser2",
            "password_hash": "test_password_hash"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
```

**Step 5: 运行测试**

```bash
cd backend
poetry run pytest tests/test_auth.py -v
```

**Step 6: Commit**

```bash
cd backend
git add app/core/security.py app/schemas/auth.py app/api/auth.py tests/test_auth.py
git commit -m "feat: implement authentication and authorization"
```

---

## 阶段 2: 核心功能实现

### Task 7: 实现商品价格记录功能

**Files:**
- Create: `backend/app/models/product.py`
- Create: `backend/app/schemas/product.py`
- Create: `backend/app/api/products.py`
- Create: `backend/tests/test_products.py`

**Step 1: 创建产品模型**

```python
from sqlalchemy import Column, Integer, String, DateTime, Decimal, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.core.database import Base


class RecordType(PyEnum):
    PURCHASE = "purchase"
    PRICE = "price"


class ProductRecord(Base):
    __tablename__ = "product_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_name = Column(String(200), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    price = Column(Decimal(10, 2), nullable=False)
    currency = Column(String(3), default="CNY")
    original_quantity = Column(Decimal(10, 3), nullable=False)
    original_unit = Column(String(20), nullable=False)
    standard_quantity = Column(Decimal(10, 3), nullable=False)
    standard_unit = Column(String(20), default="g")
    record_type = Column(String(20), default=RecordType.PURCHASE.value)
    exchange_rate = Column(Decimal(10, 6), default=1.0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String(500), nullable=True)

    # 关系
    user = relationship("User", back_populates="product_records")
    location = relationship("Location", back_populates="product_records")
```

**Step 2: 创建产品 schemas**

```python
from pydantic import BaseModel, Field, Decimal
from typing import Optional, List
from datetime import datetime


class ProductRecordCreate(BaseModel):
    product_name: str = Field(..., max_length=200)
    location_id: Optional[int] = None
    price: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = "CNY"
    original_quantity: Decimal = Field(..., gt=0)
    original_unit: str
    record_type: str = "purchase"
    notes: Optional[str] = Field(None, max_length=500)


class ProductRecordResponse(BaseModel):
    id: int
    product_name: str
    location_id: Optional[int]
    price: Decimal
    currency: str
    original_quantity: Decimal
    original_unit: str
    standard_quantity: Decimal
    standard_unit: str
    record_type: str
    exchange_rate: Decimal
    recorded_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class ProductHistoryResponse(BaseModel):
    product_name: str
    records: List[ProductRecordResponse]
```

**Step 3: 创建 products API**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import ProductRecord
from app.schemas.product import ProductRecordCreate, ProductRecordResponse, ProductHistoryResponse
from app.utils.unit_converter import convert_to_standard

router = APIRouter()


@router.post("/", response_model=ProductRecordResponse)
async def create_product_record(
    record: ProductRecordCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建商品记录"""
    # 获取当天汇率
    exchange_rate = 1.0  # TODO: 从汇率服务获取

    # 单位转换
    standard_quantity, standard_unit = convert_to_standard(
        record.original_quantity,
        record.original_unit
    )

    # 创建记录
    db_record = ProductRecord(
        user_id=current_user.id,
        product_name=record.product_name,
        location_id=record.location_id,
        price=record.price,
        currency=record.currency,
        original_quantity=record.original_quantity,
        original_unit=record.original_unit,
        standard_quantity=standard_quantity,
        standard_unit=standard_unit,
        record_type=record.record_type,
        exchange_rate=exchange_rate,
        notes=record.notes
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return db_record


@router.get("/", response_model=List[ProductRecordResponse])
async def get_product_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    product_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录列表"""
    query = db.query(ProductRecord).filter(ProductRecord.user_id == current_user.id)

    if product_name:
        query = query.filter(ProductRecord.product_name.contains(product_name))

    records = query.order_by(ProductRecord.recorded_at.desc()).offset(skip).limit(limit).all()
    return records


@router.get("/{record_id}", response_model=ProductRecordResponse)
async def get_product_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品记录详情"""
    record = db.query(ProductRecord).filter(
        ProductRecord.id == record_id,
        ProductRecord.user_id == current_user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.get("/history/{product_name}", response_model=ProductHistoryResponse)
async def get_product_history(
    product_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取商品历史价格"""
    records = db.query(ProductRecord).filter(
        ProductRecord.user_id == current_user.id,
        ProductRecord.product_name == product_name
    ).order_by(ProductRecord.recorded_at.desc()).all()

    return ProductHistoryResponse(
        product_name=product_name,
        records=records
    )
```

**Step 4: 创建单位转换工具**

```python
from decimal import Decimal
from typing import Tuple

# 重量单位转换（转换为克）
WEIGHT_CONVERSION = {
    "g": (1, "g"),
    "kg": (1000, "g"),
    "斤": (500, "g"),
    "两": (50, "g"),
    "lb": (453.592, "g"),
    "oz": (28.3495, "g"),
}

# 容量单位转换（转换为毫升）
VOLUME_CONVERSION = {
    "ml": (1, "ml"),
    "l": (1000, "ml"),
    "杯": (240, "ml"),
    "汤匙": (15, "ml"),
    "茶匙": (5, "ml"),
}


def convert_to_standard(quantity: Decimal, unit: str) -> Tuple[Decimal, str]:
    """转换为标准单位"""
    unit_lower = unit.lower()

    # 尝试重量单位
    if unit_lower in WEIGHT_CONVERSION:
        factor, standard_unit = WEIGHT_CONVERSION[unit_lower]
        return Decimal(str(quantity)) * Decimal(str(factor)), standard_unit

    # 尝试容量单位
    if unit_lower in VOLUME_CONVERSION:
        factor, standard_unit = VOLUME_CONVERSION[unit_lower]
        return Decimal(str(quantity)) * Decimal(str(factor)), standard_unit

    # 其他单位不转换
    return quantity, unit
```

**Step 5: 创建测试**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_product_record():
    # 先登录获取 token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password_hash": "test_password_hash"
        }
    )
    token = response.json()["access_token"]

    # 创建商品记录
    response = client.post(
        "/api/v1/products/",
        json={
            "product_name": "有机鸡蛋",
            "price": 12.50,
            "original_quantity": 1.5,
            "original_unit": "斤"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_name"] == "有机鸡蛋"
    assert data["price"] == "12.50"


def test_get_product_records():
    # 先登录
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    # 获取记录列表
    response = client.get(
        "/api/v1/products/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Step 6: 运行测试**

```bash
cd backend
poetry run pytest tests/test_products.py -v
```

**Step 7: Commit**

```bash
cd backend
git add app/models/product.py app/schemas/product.py app/api/products.py app/utils/unit_converter.py tests/test_products.py
git commit -m "feat: implement product price recording"
```

---

### Task 8: 实现地点管理功能

**Files:**
- Create: `backend/app/models/location.py`
- Create: `backend/app/schemas/location.py`
- Create: `backend/app/api/locations.py`
- Create: `backend/tests/test_locations.py`

**Step 1: 创建地点模型**

```python
from sqlalchemy import Column, Integer, String, DateTime, Decimal, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(String(500))
    latitude = Column(Decimal(10, 7))
    longitude = Column(Decimal(10, 7))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="locations")
    product_records = relationship("ProductRecord", back_populates="location")


class FavoriteLocation(Base):
    __tablename__ = "favorite_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    type = Column(String(50), default="other")  # home, work, other
    latitude = Column(Decimal(10, 7), nullable=False)
    longitude = Column(Decimal(10, 7), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="favorite_locations")
```

**Step 2: 创建地点 schemas**

```python
from pydantic import BaseModel, Field, Decimal
from typing import Optional, List
from datetime import datetime


class LocationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)


class LocationResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteLocationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    type: str = "other"
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)


class FavoriteLocationResponse(BaseModel):
    id: int
    name: str
    type: str
    latitude: Decimal
    longitude: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class RouteCalculateRequest(BaseModel):
    from_location_id: int
    to_location_id: int
    travel_mode: str = "driving"  # driving, walking, cycling, transit
    map_provider: str = "amap"


class RouteCalculateResponse(BaseModel):
    distance: float  # 公里
    duration: int  # 分钟
    cost: float  # 成本
    currency: str
```

**Step 3: 创建 locations API**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.location import Location, FavoriteLocation
from app.schemas.location import (
    LocationCreate,
    LocationResponse,
    FavoriteLocationCreate,
    FavoriteLocationResponse,
    RouteCalculateRequest,
    RouteCalculateResponse
)
from app.services.map_service import calculate_route

router = APIRouter()


@router.post("/", response_model=LocationResponse)
async def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建地点"""
    db_location = Location(
        user_id=current_user.id,
        name=location.name,
        address=location.address,
        latitude=location.latitude,
        longitude=location.longitude
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.get("/", response_model=List[LocationResponse])
async def get_locations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取地点列表"""
    locations = db.query(Location).filter(Location.user_id == current_user.id).all()
    return locations


@router.get("/favorites/", response_model=List[FavoriteLocationResponse])
async def get_favorite_locations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取常用位置"""
    favorites = db.query(FavoriteLocation).filter(
        FavoriteLocation.user_id == current_user.id
    ).all()
    return favorites


@router.post("/favorites/", response_model=FavoriteLocationResponse)
async def create_favorite_location(
    location: FavoriteLocationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建常用位置"""
    db_location = FavoriteLocation(
        user_id=current_user.id,
        name=location.name,
        type=location.type,
        latitude=location.latitude,
        longitude=location.longitude
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.post("/route", response_model=RouteCalculateResponse)
async def calculate_location_route(
    request: RouteCalculateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算路线"""
    # 获取起点和终点
    from_location = db.query(FavoriteLocation).filter(
        FavoriteLocation.id == request.from_location_id,
        FavoriteLocation.user_id == current_user.id
    ).first()
    if not from_location:
        raise HTTPException(status_code=404, detail="起点不存在")

    to_location = db.query(Location).filter(
        Location.id == request.to_location_id,
        Location.user_id == current_user.id
    ).first()
    if not to_location:
        raise HTTPException(status_code=404, detail="终点不存在")

    # 计算路线
    result = calculate_route(
        (float(from_location.latitude), float(from_location.longitude)),
        (float(to_location.latitude), float(to_location.longitude)),
        request.travel_mode,
        request.map_provider
    )

    return RouteCalculateResponse(**result)
```

**Step 4: 创建地图服务**

```python
import httpx
from typing import Tuple, Dict
from app.config import settings


async def calculate_route(
    from_coords: Tuple[float, float],
    to_coords: Tuple[float, float],
    travel_mode: str = "driving",
    map_provider: str = "amap"
) -> Dict:
    """计算路线"""
    # TODO: 实现各地图服务的路线规划
    # 这里先返回简单计算

    # 计算直线距离（Haversine 公式）
    distance = _haversine_distance(from_coords, to_coords)

    # 根据出行方式估算时间和成本
    if travel_mode == "driving":
        duration = int(distance / 40 * 60)  # 假设平均速度 40 km/h
        cost = distance * 0.5  # 假设每公里 0.5 元
    elif travel_mode == "walking":
        duration = int(distance / 5 * 60)  # 假设步行速度 5 km/h
        cost = 0
    elif travel_mode == "cycling":
        duration = int(distance / 15 * 60)  # 假设骑行速度 15 km/h
        cost = 0
    else:  # transit
        duration = int(distance / 30 * 60)  # 假设公交平均速度 30 km/h
        cost = distance * 1.0  # 假设每公里 1 元

    return {
        "distance": round(distance, 2),
        "duration": duration,
        "cost": round(cost, 2),
        "currency": "CNY"
    }


def _haversine_distance(
    point1: Tuple[float, float],
    point2: Tuple[float, float]
) -> float:
    """计算两点间距离（公里）"""
    import math

    lat1, lon1 = point1
    lat2, lon2 = point2

    # 将经纬度转换为弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine 公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # 地球半径（公里）
    r = 6371

    return c * r
```

**Step 5: 创建测试**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_location():
    # 先登录
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    # 创建地点
    response = client.post(
        "/api/v1/locations/",
        json={
            "name": "沃尔玛",
            "address": "北京市朝阳区",
            "latitude": 39.9042,
            "longitude": 116.4074
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "沃尔玛"
```

**Step 6: 运行测试**

```bash
cd backend
poetry run pytest tests/test_locations.py -v
```

**Step 7: Commit**

```bash
cd backend
git add app/models/location.py app/schemas/location.py app/api/locations.py app/services/map_service.py tests/test_locations.py
git commit -m "feat: implement location management"
```

---

### Task 9: 实现营养数据库模块

**Files:**
- Create: `backend/app/models/nutrition.py`
- Create: `backend/app/schemas/nutrition.py`
- Create: `backend/app/api/nutrition.py`
- Create: `backend/app/services/nutrition_service.py`
- Create: `backend/tests/test_nutrition.py`

**Step 1: 创建营养数据模型**

```python
from sqlalchemy import Column, Integer, String, DateTime, Decimal
from sqlalchemy.sql import func
from app.core.database import Base


class NutritionData(Base):
    __tablename__ = "nutrition_data"

    id = Column(Integer, primary_key=True, index=True)
    usda_id = Column(String(50), unique=True, index=True)
    name_en = Column(String(200), nullable=False)
    name_zh = Column(String(200))
    calories = Column(Decimal(10, 2))  # 卡路里
    protein = Column(Decimal(10, 2))  # 蛋白质 (g)
    fat = Column(Decimal(10, 2))  # 脂肪 (g)
    carbs = Column(Decimal(10, 2))  # 碳水化合物 (g)
    fiber = Column(Decimal(10, 2))  # 纤维 (g)
    sugar = Column(Decimal(10, 2))  # 糖分 (g)
    sodium = Column(Decimal(10, 2))  # 钠 (mg)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"))
    aliases = Column(String(1000))  # JSON 字符串
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IngredientNutritionMapping(Base):
    __tablename__ = "ingredient_nutrition_mapping"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"), nullable=False)
    priority = Column(Integer, default=0)
    confidence = Column(Decimal(3, 2), default=1.00)  # 置信度 0.00-1.00
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Step 2: 创建营养数据 schemas**

```python
from pydantic import BaseModel, Field, Decimal
from typing import Optional, List


class NutritionDataResponse(BaseModel):
    id: int
    usda_id: str
    name_en: str
    name_zh: Optional[str]
    calories: Optional[Decimal]
    protein: Optional[Decimal]
    fat: Optional[Decimal]
    carbs: Optional[Decimal]
    fiber: Optional[Decimal]
    sugar: Optional[Decimal]
    sodium: Optional[Decimal]

    class Config:
        from_attributes = True


class IngredientMatch(BaseModel):
    nutrition_id: int
    name_en: str
    name_zh: Optional[str]
    confidence: Decimal


class NutritionMatchResponse(BaseModel):
    matches: List[IngredientMatch]


class NutritionCorrectRequest(BaseModel):
    ingredient_name: str
    nutrition_id: int
```

**Step 3: 创建营养服务**

```python
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from app.models.nutrition import Ingredient, NutritionData, IngredientNutritionMapping
from decimal import Decimal
import json


async def search_nutrition(
    query: str,
    fuzzy: bool = False,
    limit: int = 10,
    db: Session = None
) -> List[Dict]:
    """搜索营养数据"""
    results = []

    # 精确匹配
    exact_matches = db.query(NutritionData).filter(
        (NutritionData.name_zh == query) | (NutritionData.name_en.ilike(f"%{query}%"))
    ).limit(limit).all()

    for match in exact_matches:
        results.append({
            "nutrition_id": match.id,
            "name_en": match.name_en,
            "name_zh": match.name_zh,
            "confidence": Decimal("1.00")
        })

    # 模糊匹配
    if fuzzy and len(results) < limit:
        fuzzy_matches = db.query(NutritionData).filter(
            NutritionData.name_zh.contains(query)
        ).limit(limit - len(results)).all()

        for match in fuzzy_matches:
            if match.id not in [r["nutrition_id"] for r in results]:
                results.append({
                    "nutrition_id": match.id,
                    "name_en": match.name_en,
                    "name_zh": match.name_zh,
                    "confidence": Decimal("0.70")
                })

    return results[:limit]


async def match_ingredient(
    ingredient_name: str,
    db: Session = None
) -> List[Dict]:
    """匹配食材到营养数据（混合推荐算法）"""

    matches = []

    # 1. 优先查找映射表精确匹配
    ingredient = db.query(Ingredient).filter(
        Ingredient.name == ingredient_name
    ).first()

    if ingredient and ingredient.aliases:
        aliases = json.loads(ingredient.aliases)
        for alias_name in aliases:
            matches.extend(await search_nutrition(alias_name, db=db))

    # 2. 未匹配则关键词模糊搜索
    if not matches:
        # 提取关键词
        keywords = _extract_keywords(ingredient_name)
        for keyword in keywords:
            matches.extend(await search_nutrition(keyword, fuzzy=True, db=db))

    # 3. 去重并排序
    unique_matches = {}
    for match in matches:
        key = match["nutrition_id"]
        if key not in unique_matches:
            unique_matches[key] = match
        else:
            # 取更高的置信度
            if match["confidence"] > unique_matches[key]["confidence"]:
                unique_matches[key] = match

    # 按置信度排序
    sorted_matches = sorted(
        unique_matches.values(),
        key=lambda x: x["confidence"],
        reverse=True
    )

    return sorted_matches[:5]


def _extract_keywords(text: str) -> List[str]:
    """提取关键词"""
    # 简单实现：去除形容词和量词
    stopwords = ["有机", "新鲜", "进口", "特级", "精选", "个大", ""]

    keywords = [text]
    for word in stopwords:
        if word in text:
            keywords.append(text.replace(word, ""))

    return list(set([k for k in keywords if k]))


async def correct_mapping(
    ingredient_name: str,
    nutrition_id: int,
    db: Session = None
) -> bool:
    """更正映射并学习"""
    # 查找或创建食材
    ingredient = db.query(Ingredient).filter(
        Ingredient.name == ingredient_name
    ).first()

    if not ingredient:
        # 获取营养数据
        nutrition = db.query(NutritionData).filter(
            NutritionData.id == nutrition_id
        ).first()
        if not nutrition:
            return False

        ingredient = Ingredient(
            name=ingredient_name,
            nutrition_id=nutrition_id,
            aliases=json.dumps([ingredient_name])
        )
        db.add(ingredient)
    else:
        # 更新映射
        ingredient.nutrition_id = nutrition_id
        aliases = json.loads(ingredient.aliases) if ingredient.aliases else []
        if ingredient_name not in aliases:
            aliases.append(ingredient_name)
        ingredient.aliases = json.dumps(aliases)

    # 创建或更新映射
    mapping = db.query(IngredientNutritionMapping).filter(
        IngredientNutritionMapping.ingredient_id == ingredient.id,
        IngredientNutritionMapping.nutrition_id == nutrition_id
    ).first()

    if mapping:
        mapping.confidence = Decimal("1.00")
        mapping.priority += 1
    else:
        mapping = IngredientNutritionMapping(
            ingredient_id=ingredient.id,
            nutrition_id=nutrition_id,
            priority=1,
            confidence=Decimal("1.00")
        )
        db.add(mapping)

    db.commit()
    return True
```

**Step 4: 创建 nutrition API**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.nutrition import (
    NutritionDataResponse,
    NutritionMatchResponse,
    NutritionCorrectRequest
)
from app.services.nutrition_service import (
    search_nutrition,
    match_ingredient,
    correct_mapping
)

router = APIRouter()


@router.get("/search", response_model=List[NutritionDataResponse])
async def search_nutrition_data(
    query: str = Query(..., min_length=1),
    fuzzy: bool = Query(False),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """搜索营养数据"""
    results = await search_nutrition(query, fuzzy=fuzzy, limit=limit, db=db)
    return results


@router.post("/match", response_model=NutritionMatchResponse)
async def match_ingredient_nutrition(
    ingredient_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """匹配食材到营养数据"""
    matches = await match_ingredient(ingredient_name, db=db)
    return NutritionMatchResponse(matches=matches)


@router.post("/correct")
async def correct_nutrition_mapping(
    request: NutritionCorrectRequest,
    db: Session = Depends(get_db)
):
    """更正映射"""
    success = await correct_mapping(
        request.ingredient_name,
        request.nutrition_id,
        db=db
    )
    if not success:
        return {"success": False, "message": "更正失败"}
    return {"success": True, "message": "更正成功"}
```

**Step 5: 创建测试**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_nutrition():
    response = client.get("/api/v1/nutrition/search?query=鸡蛋")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_match_ingredient():
    response = client.post("/api/v1/nutrition/match?ingredient_name=有机鸡蛋")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
```

**Step 6: 运行测试**

```bash
cd backend
poetry run pytest tests/test_nutrition.py -v
```

**Step 7: Commit**

```bash
cd backend
git add app/models/nutrition.py app/schemas/nutrition.py app/api/nutrition.py app/services/nutrition_service.py tests/test_nutrition.py
git commit -m "feat: implement nutrition database module"
```

---

## 阶段 3: 菜谱和报告功能

### Task 10: 实现菜谱功能

**Files:**
- Create: `backend/app/models/recipe.py`
- Create: `backend/app/schemas/recipe.py`
- Create: `backend/app/api/recipes.py`
- Create: `backend/app/services/recipe_service.py`
- Create: `backend/tests/test_recipes.py`

**Step 1: 创建菜谱模型**

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    source = Column(String(100))  # HowToCook, custom
    user_id = Column(Integer, ForeignKey("users.id"))
    tags = Column(JSON)  # 标签列表
    cooking_steps = Column(JSON)  # 做法步骤
    total_time_minutes = Column(Integer)
    difficulty = Column(String(20))  # simple, medium, complex
    servings = Column(Integer, default=1)
    tips = Column(JSON)  # 小贴士
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(String(50), nullable=False)
    unit = Column(String(20))

    # 关系
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient")
```

**Step 2: 创建菜谱 schemas**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CookingStep(BaseModel):
    step: int
    content: str
    duration_minutes: Optional[int] = None


class RecipeIngredientCreate(BaseModel):
    ingredient_name: str
    quantity: str
    unit: Optional[str] = None


class RecipeCreate(BaseModel):
    name: str = Field(..., max_length=200)
    source: str = "custom"
    tags: Optional[List[str]] = []
    cooking_steps: List[CookingStep]
    ingredients: List[RecipeIngredientCreate]
    total_time_minutes: Optional[int] = None
    difficulty: Optional[str] = "simple"
    servings: int = 1
    tips: Optional[List[str]] = []


class RecipeIngredientDetail(BaseModel):
    ingredient_id: int
    name: str
    quantity: str
    unit: Optional[str]
    nutrition_info: Optional[dict] = None


class RecipeResponse(BaseModel):
    id: int
    name: str
    source: str
    tags: Optional[List[str]]
    cooking_steps: Optional[List[CookingStep]]
    total_time_minutes: Optional[int]
    difficulty: Optional[str]
    servings: int
    tips: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecipeDetailResponse(RecipeResponse):
    ingredients: List[RecipeIngredientDetail]


class RecipeCostResponse(BaseModel):
    total_cost: Decimal
    currency: str
    cost_per_serving: Decimal
    cost_breakdown: List[dict]


class RecipeNutritionResponse(BaseModel):
    total_calories: Optional[Decimal]
    total_protein: Optional[Decimal]
    total_fat: Optional[Decimal]
    total_carbs: Optional[Decimal]
    per_serving: dict
```

**Step 3: 创建菜谱服务**

```python
from sqlalchemy.orm import Session
from typing import Dict, List
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product import ProductRecord
from app.models.nutrition import Ingredient, NutritionData
from decimal import Decimal
import json


async def calculate_recipe_cost(
    recipe_id: int,
    user_id: int,
    db: Session = None
) -> Dict:
    """计算菜谱成本"""
    # 获取菜谱
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_cost = Decimal("0.00")
    cost_breakdown = []

    # 遍历食材
    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 查找用户最新的价格记录
        latest_record = db.query(ProductRecord).filter(
            ProductRecord.user_id == user_id,
            ProductRecord.product_name.contains(ingredient.name)
        ).order_by(ProductRecord.recorded_at.desc()).first()

        if latest_record:
            # 简单计算（假设数量是标准单位）
            # TODO: 实现更复杂的数量转换和成本计算
            cost = Decimal(str(latest_record.price))
            total_cost += cost

            cost_breakdown.append({
                "ingredient_name": ingredient.name,
                "cost": float(cost),
                "unit_price": float(latest_record.price)
            })

    return {
        "total_cost": total_cost,
        "currency": "CNY",
        "cost_per_serving": total_cost / (recipe.servings or 1),
        "cost_breakdown": cost_breakdown
    }


async def calculate_recipe_nutrition(
    recipe_id: int,
    db: Session = None
) -> Dict:
    """计算菜谱营养"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_calories = Decimal("0.00")
    total_protein = Decimal("0.00")
    total_fat = Decimal("0.00")
    total_carbs = Decimal("0.00")

    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient
        if ingredient.nutrition_id:
            nutrition = db.query(NutritionData).filter(
                NutritionData.id == ingredient.nutrition_id
            ).first()
            if nutrition:
                total_calories += Decimal(str(nutrition.calories or 0))
                total_protein += Decimal(str(nutrition.protein or 0))
                total_fat += Decimal(str(nutrition.fat or 0))
                total_carbs += Decimal(str(nutrition.carbs or 0))

    servings = recipe.servings or 1

    return {
        "total_calories": total_calories,
        "total_protein": total_protein,
        "total_fat": total_fat,
        "total_carbs": total_carbs,
        "per_serving": {
            "calories": total_calories / servings,
            "protein": total_protein / servings,
            "fat": total_fat / servings,
            "carbs": total_carbs / servings
        }
    }
```

**Step 4: 创建 recipes API**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.schemas.recipe import (
    RecipeCreate,
    RecipeResponse,
    RecipeDetailResponse,
    RecipeCostResponse,
    RecipeNutritionResponse
)
from app.services.recipe_service import calculate_recipe_cost, calculate_recipe_nutrition

router = APIRouter()


@router.post("/", response_model=RecipeResponse)
async def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建菜谱"""
    # 创建菜谱
    db_recipe = Recipe(
        name=recipe.name,
        source=recipe.source,
        user_id=current_user.id,
        tags=recipe.tags,
        cooking_steps=[s.model_dump() for s in recipe.cooking_steps],
        total_time_minutes=recipe.total_time_minutes,
        difficulty=recipe.difficulty,
        servings=recipe.servings,
        tips=recipe.tips
    )
    db.add(db_recipe)
    db.flush()

    # 创建食材关联
    for ingredient_data in recipe.ingredients:
        # 查找或创建食材
        ingredient = db.query(Ingredient).filter(
            Ingredient.name == ingredient_data.ingredient_name
        ).first()
        if not ingredient:
            ingredient = Ingredient(name=ingredient_data.ingredient_name)
            db.add(ingredient)
            db.flush()

        # 创建关联
        recipe_ingredient = RecipeIngredient(
            recipe_id=db_recipe.id,
            ingredient_id=ingredient.id,
            quantity=ingredient_data.quantity,
            unit=ingredient_data.unit
        )
        db.add(recipe_ingredient)

    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.get("/", response_model=List[RecipeResponse])
async def get_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱列表"""
    query = db.query(Recipe)

    if tag:
        # 简单的 JSON 查询
        query = query.filter(Recipe.tags.contains([tag]))

    recipes = query.offset(skip).limit(limit).all()
    return recipes


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
async def get_recipe_detail(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱详情"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="菜谱不存在")

    # 构建响应
    ingredients_detail = []
    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient
        ingredients_detail.append({
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "quantity": recipe_ingredient.quantity,
            "unit": recipe_ingredient.unit
        })

    return {
        "id": recipe.id,
        "name": recipe.name,
        "source": recipe.source,
        "tags": recipe.tags,
        "cooking_steps": recipe.cooking_steps,
        "total_time_minutes": recipe.total_time_minutes,
        "difficulty": recipe.difficulty,
        "servings": recipe.servings,
        "tips": recipe.tips,
        "created_at": recipe.created_at,
        "updated_at": recipe.updated_at,
        "ingredients": ingredients_detail
    }


@router.get("/{recipe_id}/cost", response_model=RecipeCostResponse)
async def get_recipe_cost(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱成本"""
    result = await calculate_recipe_cost(recipe_id, current_user.id, db)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result


@router.get("/{recipe_id}/nutrition", response_model=RecipeNutritionResponse)
async def get_recipe_nutrition(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱营养"""
    result = await calculate_recipe_nutrition(recipe_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    return result
```

**Step 5: 创建测试**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_recipe():
    # 先登录
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    # 创建菜谱
    response = client.post(
        "/api/v1/recipes/",
        json={
            "name": "番茄炒蛋",
            "source": "custom",
            "tags": ["家常菜"],
            "cooking_steps": [
                {"step": 1, "content": "番茄切块，鸡蛋打散"}
            ],
            "ingredients": [
                {"ingredient_name": "鸡蛋", "quantity": "2", "unit": "个"}
            ],
            "servings": 2
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "番茄炒蛋"
```

**Step 6: 运行测试**

```bash
cd backend
poetry run pytest tests/test_recipes.py -v
```

**Step 7: Commit**

```bash
cd backend
git add app/models/recipe.py app/schemas/recipe.py app/api/recipes.py app/services/recipe_service.py tests/test_recipes.py
git commit -m "feat: implement recipe management"
```

---

### Task 11: 实现报告功能

**Files:**
- Create: `backend/app/models/expense.py`
- Create: `backend/app/schemas/report.py`
- Create: `backend/app/api/reports.py`
- Create: `backend/app/services/report_service.py`
- Create: `backend/tests/test_reports.py`

**Step 1: 创建费用模型**

```python
from sqlalchemy import Column, Integer, String, Date, Decimal, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.core.database import Base


class ExpenseType(PyEnum):
    WATER = "water"
    GAS = "gas"
    ELECTRICITY = "electricity"
    TRANSPORT = "transport"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(20), nullable=False)  # water, gas, electricity, transport
    amount = Column(Decimal(10, 2), nullable=False)
    unit = Column(String(20))
    date = Column(Date, nullable=False)
    notes = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="expenses")
```

**Step 2: 创建报告 schemas**

```python
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal


class ExpenseCreate(BaseModel):
    type: str  # water, gas, electricity, transport
    amount: Decimal
    unit: Optional[str] = None
    date: date
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    type: str
    amount: Decimal
    unit: Optional[str]
    date: date
    notes: Optional[str]

    class Config:
        from_attributes = True


class ReportRequest(BaseModel):
    start_date: date
    end_date: date
    category: str = "all"  # all, food, transport, utility
    granularity: str = "daily"  # daily, weekly, monthly


class ExpenseReportResponse(BaseModel):
    total_expense: Decimal
    currency: str
    category_breakdown: Dict[str, Decimal]
    time_series: List[Dict]


class NutritionTrendResponse(BaseModel):
    time_series: List[Dict]
    averages: Dict[str, Decimal]


class PriceTrendResponse(BaseModel):
    product_name: str
    time_series: List[Dict]


class LocationAnalysisResponse(BaseModel):
    location_name: str
    products: List[Dict]
    avg_price: Decimal
    value_score: Decimal
```

**Step 3: 创建报告服务**

```python
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Dict, List
from app.models.product import ProductRecord
from app.models.expense import Expense
from app.models.recipe import Recipe
from datetime import date
from decimal import Decimal


async def generate_expense_report(
    user_id: int,
    start_date: date,
    end_date: date,
    db: Session = None
) -> Dict:
    """生成支出报告"""
    # 商品支出
    product_expenses = db.query(
        func.sum(ProductRecord.price).label('total')
    ).filter(
        ProductRecord.user_id == user_id,
        ProductRecord.recorded_at >= start_date,
        ProductRecord.recorded_at <= end_date
    ).first()

    food_total = product_expenses.total or Decimal("0.00")

    # 其他费用支出
    utility_expenses = db.query(
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == user_id,
        Expense.date >= start_date,
        Expense.date <= end_date,
        Expense.type.in_(["water", "gas", "electricity"])
    ).first()

    utility_total = utility_expenses.total or Decimal("0.00")

    transport_expenses = db.query(
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == user_id,
        Expense.date >= start_date,
        Expense.date <= end_date,
        Expense.type == "transport"
    ).first()

    transport_total = transport_expenses.total or Decimal("0.00")

    total_expense = food_total + utility_total + transport_total

    # 时间序列数据
    time_series = []
    current_date = start_date
    while current_date <= end_date:
        day_total = db.query(
            func.sum(ProductRecord.price).label('total')
        ).filter(
            ProductRecord.user_id == user_id,
            func.date(ProductRecord.recorded_at) == current_date
        ).first()

        time_series.append({
            "date": current_date.isoformat(),
            "amount": float(day_total.total or 0)
        })
        current_date += timedelta(days=1)

    return {
        "total_expense": total_expense,
        "currency": "CNY",
        "category_breakdown": {
            "food": float(food_total),
            "utility": float(utility_total),
            "transport": float(transport_total)
        },
        "time_series": time_series
    }


async def generate_price_trend(
    user_id: int,
    product_name: str,
    db: Session = None
) -> Dict:
    """生成价格趋势"""
    records = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id,
        ProductRecord.product_name.contains(product_name)
    ).order_by(ProductRecord.recorded_at).all()

    time_series = []
    for record in records:
        time_series.append({
            "date": record.recorded_at.strftime("%Y-%m-%d"),
            "price": float(record.price),
            "currency": record.currency
        })

    return {
        "product_name": product_name,
        "time_series": time_series
    }
```

**Step 4: 创建 reports API**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.expense import Expense
from app.schemas.report import (
    ExpenseCreate,
    ExpenseResponse,
    ReportRequest,
    ExpenseReportResponse,
    PriceTrendResponse
)
from app.services.report_service import generate_expense_report, generate_price_trend

router = APIRouter()


@router.post("/expenses/", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建费用记录"""
    db_expense = Expense(
        user_id=current_user.id,
        type=expense.type,
        amount=expense.amount,
        unit=expense.unit,
        date=expense.date,
        notes=expense.notes
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.get("/expenses/", response_model=list[ExpenseResponse])
async def get_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取费用记录"""
    query = db.query(Expense).filter(Expense.user_id == current_user.id)

    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)

    return query.order_by(Expense.date.desc()).all()


@router.get("/expense", response_model=ExpenseReportResponse)
async def get_expense_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取支出报告"""
    result = await generate_expense_report(
        current_user.id,
        start_date,
        end_date,
        db
    )
    return result


@router.get("/price-trend", response_model=PriceTrendResponse)
async def get_price_trend(
    product_name: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取价格趋势"""
    result = await generate_price_trend(current_user.id, product_name, db)
    return result
```

**Step 5: 创建测试**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from datetime import date

client = TestClient(app)


def test_create_expense():
    # 先登录
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    # 创建费用
    response = client.post(
        "/api/v1/reports/expenses/",
        json={
            "type": "water",
            "amount": 15.5,
            "unit": "立方米",
            "date": "2024-01-15"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "water"


def test_get_expense_report():
    response = client.get("/api/v1/reports/expense?start_date=2024-01-01&end_date=2024-01-31")
    # 需要登录
    assert response.status_code in [200, 401]
```

**Step 6: 运行测试**

```bash
cd backend
poetry run pytest tests/test_reports.py -v
```

**Step 7: Commit**

```bash
cd backend
git add app/models/expense.py app/schemas/report.py app/api/reports.py app/services/report_service.py tests/test_reports.py
git commit -m "feat: implement reports functionality"
```

---

## 阶段 4: 前端实现

### Task 12: 初始化前端项目

**Step 1: 安装依赖并创建基础结构**

```bash
cd frontend
npm install
npm run dev
```

**Step 2: 创建基础文件**

```typescript
// src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
```

```vue
<!-- src/App.vue -->
<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<style>
#app {
  min-height: 100vh;
  background-color: #f5f5f5;
}
</style>
```

**Step 3: 创建路由配置**

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/dashboard/Dashboard.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/Login.vue')
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/Register.vue')
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('@/views/products/ProductList.vue')
  },
  {
    path: '/recipes',
    name: 'recipes',
    component: () => import('@/views/recipes/RecipeList.vue')
  },
  {
    path: '/locations',
    name: 'locations',
    component: () => import('@/views/locations/LocationMap.vue')
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/reports/ReportOverview.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

**Step 4: 创建 API 客户端**

```typescript
// src/api/client.ts
class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || '/api/v1'
    this.token = localStorage.getItem('token')
  }

  setToken(token: string) {
    this.token = token
    localStorage.setItem('token', token)
  }

  clearToken() {
    this.token = null
    localStorage.removeItem('token')
  }

  private async request<T>(
    method: string,
    path: string,
    data?: any
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json'
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const options: RequestInit = {
      method,
      headers
    }

    if (data) {
      options.body = JSON.stringify(data)
    }

    const response = await fetch(`${this.baseURL}${path}`, options)

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '请求失败')
    }

    return response.json()
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path)
  }

  async post<T>(path: string, data?: any): Promise<T> {
    return this.request<T>('POST', path, data)
  }

  async put<T>(path: string, data?: any): Promise<T> {
    return this.request<T>('PUT', path, data)
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path)
  }
}

export const api = new ApiClient()
```

**Step 5: 创建 Pinia store**

```typescript
// src/stores/user.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'

interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password_hash: string) {
    const response = await api.post('/auth/login', {
      username,
      password_hash
    })
    token.value = response.access_token
    api.setToken(response.access_token)
    await fetchUser()
    return response
  }

  async function register(data: any) {
    const response = await api.post('/auth/register', data)
    token.value = response.access_token
    api.setToken(response.access_token)
    return response
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await api.get('/auth/me')
    } catch (error) {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    api.clearToken()
    localStorage.removeItem('token')
  }

  return {
    user,
    token,
    isLoggedIn,
    login,
    register,
    fetchUser,
    logout
  }
})
```

**Step 6: Commit**

```bash
cd frontend
git add .
git commit -m "chore: initialize frontend project structure"
```

---

### Task 13: 创建认证页面

**Files:**
- Create: `frontend/src/views/auth/Login.vue`
- Create: `frontend/src/views/auth/Register.vue`

**Step 1: 创建登录页面**

```vue
<!-- src/views/auth/Login.vue -->
<template>
  <div class="login-container">
    <div class="login-card">
      <h1>生计</h1>
      <h2>生活成本计算器</h2>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            required
            placeholder="请输入用户名"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            required
            placeholder="请输入密码"
          />
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="links">
        <router-link to="/register">注册新账号</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import * as crypto from 'crypto-js/sha256'

const router = useRouter()
const userStore = useUserStore()

const formData = ref({
  username: '',
  password: ''
})
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    // SHA256 加密密码
    const password_hash = crypto(formData.value.password).toString()

    await userStore.login(formData.value.username, password_hash)
    router.push('/')
  } catch (error: any) {
    alert(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.login-card h1 {
  font-size: 2rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.login-card h2 {
  font-size: 1rem;
  color: #666;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.btn-primary {
  width: 100%;
  padding: 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 1rem;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.links {
  margin-top: 1.5rem;
  text-align: center;
}

.links a {
  color: #667eea;
  text-decoration: none;
}

.links a:hover {
  text-decoration: underline;
}
</style>
```

**Step 2: 创建注册页面**

```vue
<!-- src/views/auth/Register.vue -->
<template>
  <div class="register-container">
    <div class="register-card">
      <h1>注册</h1>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="formData.username"
            type="text"
            required
            placeholder="3-50个字符"
          />
        </div>

        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="formData.email"
            type="email"
            required
            placeholder="your@email.com"
          />
        </div>

        <div class="form-group">
          <label for="phone">手机号（可选）</label>
          <input
            id="phone"
            v-model="formData.phone"
            type="tel"
            placeholder="请输入手机号"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="formData.password"
            type="password"
            required
            placeholder="请输入密码"
          />
        </div>

        <div class="form-group" v-if="requireInviteCode">
          <label for="inviteCode">邀请码</label>
          <input
            id="inviteCode"
            v-model="formData.invite_code"
            type="text"
            required
            placeholder="请输入邀请码"
          />
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="links">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import * as crypto from 'crypto-js/sha256'

const router = useRouter()
const userStore = useUserStore()

const formData = ref({
  username: '',
  email: '',
  phone: '',
  password: '',
  invite_code: ''
})
const loading = ref(false)
const requireInviteCode = ref(false)

onMounted(async () => {
  // 检查是否需要邀请码
  try {
    const config = await fetch('/api/v1/config').then(r => r.json())
    requireInviteCode.value = config.registration_require_invite_code
  } catch (error) {
    // 忽略错误
  }
})

async function handleRegister() {
  loading.value = true
  try {
    const password_hash = crypto(formData.value.password).toString()

    await userStore.register({
      ...formData.value,
      password_hash
    })
    router.push('/')
  } catch (error: any) {
    alert(error.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.register-card h1 {
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.btn-primary {
  width: 100%;
  padding: 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 1rem;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.links {
  margin-top: 1.5rem;
  text-align: center;
}

.links a {
  color: #667eea;
  text-decoration: none;
}

.links a:hover {
  text-decoration: underline;
}
</style>
```

**Step 3: Commit**

```bash
cd frontend
git add src/views/auth/
git commit -m "feat: add login and register pages"
```

---

### Task 14: 创建仪表盘页面

**Files:**
- Create: `frontend/src/views/dashboard/Dashboard.vue`

**Step 1: 创建仪表盘组件**

```vue
<!-- src/views/dashboard/Dashboard.vue -->
<template>
  <div class="dashboard">
    <header class="dashboard-header">
      <h1>欢迎回来，{{ user?.username }}！</h1>
      <button @click="handleLogout" class="btn-logout">退出</button>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <h3>本月支出</h3>
        <p class="stat-value">¥{{ monthlyExpense.toFixed(2) }}</p>
      </div>

      <div class="stat-card">
        <h3>记录数量</h3>
        <p class="stat-value">{{ recordCount }}</p>
      </div>

      <div class="stat-card">
        <h3>菜谱数量</h3>
        <p class="stat-value">{{ recipeCount }}</p>
      </div>
    </div>

    <div class="quick-actions">
      <router-link to="/products/new" class="action-card">
        <span class="icon">📝</span>
        <span>记录商品</span>
      </router-link>
      <router-link to="/recipes/new" class="action-card">
        <span class="icon">🍳</span>
        <span>创建菜谱</span>
      </router-link>
      <router-link to="/locations/new" class="action-card">
        <span class="icon">📍</span>
        <span>添加地点</span>
      </router-link>
      <router-link to="/reports" class="action-card">
        <span class="icon">📊</span>
        <span>查看报告</span>
      </router-link>
    </div>

    <div class="recent-records">
      <h2>最近记录</h2>
      <div v-if="recentRecords.length === 0" class="empty-state">
        暂无记录，开始添加吧！
      </div>
      <div v-else class="record-list">
        <div v-for="record in recentRecords" :key="record.id" class="record-item">
          <div class="record-info">
            <span class="record-name">{{ record.product_name }}</span>
            <span class="record-date">{{ formatDate(record.recorded_at) }}</span>
          </div>
          <span class="record-price">¥{{ record.price }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api } from '@/api/client'

const router = useRouter()
const userStore = useUserStore()

const user = computed(() => userStore.user)
const monthlyExpense = ref(0)
const recordCount = ref(0)
const recipeCount = ref(0)
const recentRecords = ref<any[]>([])

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  try {
    // 获取统计数据
    const today = new Date()
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)

    const expenseReport = await api.get(
      `/reports/expense?start_date=${firstDay.toISOString().split('T')[0]}&end_date=${today.toISOString().split('T')[0]}`
    )
    monthlyExpense.value = expenseReport.total_expense

    // 获取记录数量
    const records = await api.get('/products/?limit=1')
    recordCount.value = records.length

    // 获取菜谱数量
    const recipes = await api.get('/recipes/?limit=1')
    recipeCount.value = recipes.length

    // 获取最近记录
    recentRecords.value = await api.get('/products/?limit=10')
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.dashboard {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  font-size: 1.5rem;
  color: #333;
}

.btn-logout {
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  color: #333;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-card h3 {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.action-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
  text-decoration: none;
  color: #333;
  transition: transform 0.2s, box-shadow 0.2s;
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.action-card .icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 0.5rem;
}

.recent-records {
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.recent-records h2 {
  font-size: 1.25rem;
  color: #333;
  margin-bottom: 1rem;
}

.empty-state {
  color: #999;
  text-align: center;
  padding: 2rem;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.record-item:last-child {
  border-bottom: none;
}

.record-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.record-name {
  font-weight: 500;
  color: #333;
}

.record-date {
  font-size: 0.75rem;
  color: #999;
}

.record-price {
  font-weight: bold;
  color: #42b883;
}
</style>
```

**Step 2: Commit**

```bash
cd frontend
git add src/views/dashboard/
git commit -m "feat: add dashboard page"
```

---

## 阶段 5: 部署和文档

### Task 15: 创建部署文档

**Files:**
- Create: `README.md`
- Create: `DEPLOYMENT.md`

**Step 1: 创建主 README**

```markdown
# 生计 - 生活成本计算器

> 记录商品价格，计算烹饪成本，优化生活开支

## 功能特性

- 📝 商品价格记录
- 🍳 菜谱成本计算
- 🥗 营养成分分析
- 📍 地图与路线规划
- 📊 生活成本报告
- 💰 多币种支持
- 🌏 多单位转换

## 快速开始

### Docker 部署

```bash
# 克隆代码
git clone https://github.com/your-repo/live_calc.git
cd live_calc

# 启动服务
docker-compose up -d

# 访问应用
# 前端: http://localhost
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 本地开发

#### 后端

```bash
cd backend

# 安装依赖
poetry install

# 配置环境变量
cp .env.example .env

# 初始化数据库
poetry run alembic upgrade head

# 启动服务
poetry run uvicorn app.main:app --reload
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Celery
- **前端**: Vue 3, Vite, Pinia
- **数据库**: SQLite, PostgreSQL, MySQL
- **容器**: Docker, Docker Compose

## 许可证

MIT License
```

**Step 2: 创建部署文档**

```markdown
# 部署指南

## Docker 部署

### 准备工作

1. 安装 Docker 和 Docker Compose
2. 准备服务器环境

### 快速部署

```bash
# 1. 克隆代码
git clone https://github.com/your-repo/live_calc.git
cd live_calc

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，修改相关配置

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

### 配置说明

关键环境变量：

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@db:5432/livecalc

# 安全
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# 地图服务（可选）
AMAP_API_KEY=your-amap-key
BAIDU_API_KEY=your-baidu-key
```

### 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 数据库迁移
docker-compose exec backend alembic upgrade head
```

## 直接部署

### 后端

```bash
# 安装 Python 3.11+
python --version

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env

# 初始化数据库
alembic upgrade head

# 启动服务（使用 gunicorn）
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 前端

```bash
# 构建
npm run build

# 使用 nginx 托管
# 将 dist 目录复制到 nginx 静态文件目录
```

## Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        root /path/to/dist;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## SSL 配置

使用 Let's Encrypt：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 备份

### 数据库备份

```bash
# PostgreSQL
docker-compose exec db pg_dump -U livecalc livecalc > backup.sql

# SQLite
cp backend/data/livecalc.db backup.db
```

### 恢复

```bash
# PostgreSQL
docker-compose exec -T db psql -U livecalc livecalc < backup.sql

# SQLite
cp backup.db backend/data/livecalc.db
```
```

**Step 3: Commit**

```bash
cd ..
git add README.md DEPLOYMENT.md
git commit -m "docs: add deployment documentation"
```

---

### Task 16: 创建最终提交

**Step 1: 检查所有变更**

```bash
git status
git log --oneline -10
```

**Step 2: 创建最终标签**

```bash
git tag -a v0.1.0 -m "Initial release - MVP complete"
```

**Step 3: 推送（如需要）**

```bash
git push origin main
git push origin v0.1.0
```

---

## 总结

本实施计划涵盖了生计项目的完整开发流程：

1. **阶段 0**: 项目初始化
2. **阶段 1**: 后端基础架构
3. **阶段 2**: 核心功能实现
4. **阶段 3**: 菜谱和报告功能
5. **阶段 4**: 前端实现
6. **阶段 5**: 部署和文档

每个任务都遵循 TDD 原则，包含测试、实现和提交步骤。

---

**Plan Version:** 1.0
**Last Updated:** 2026-02-25
