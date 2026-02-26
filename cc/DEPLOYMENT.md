# 部署指南

本文档提供生计项目的详细部署指南，包括 Docker 部署和直接部署两种方式。

## 目录

- [Docker 部署](#docker-部署)
- [直接部署](#直接部署)
- [Nginx 配置](#nginx-配置)
- [SSL 配置](#ssl-配置)
- [备份与恢复](#备份与恢复)
- [监控与日志](#监控与日志)
- [常见问题](#常见问题)

---

## Docker 部署（推荐）

### 准备工作

1. **安装 Docker 和 Docker Compose**

   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io docker-compose

   # CentOS/RHEL
   sudo yum install docker docker-compose

   # 验证安装
   docker --version
   docker-compose --version
   ```

2. **准备服务器环境**

   - 最低配置: 2 CPU, 4GB RAM, 20GB 磁盘
   - 推荐配置: 4 CPU, 8GB RAM, 50GB 磁盘
   - 操作系统: Ubuntu 20.04+, CentOS 8+

### 快速部署

```bash
# 1. 克隆代码
git clone https://github.com/your-repo/live_calc.git
cd live_calc

# 2. 复制环境变量配置
cp backend/.env.example backend/.env

# 3. 编辑环境变量
nano backend/.env
# 修改以下关键配置：
#   - SECRET_KEY: 生产环境的密钥
#   - JWT_SECRET_KEY: JWT 签名密钥
#   - DATABASE_URL: 生产数据库连接

# 4. 构建并启动服务
docker-compose up -d --build

# 5. 查看服务状态
docker-compose ps

# 6. 查看日志
docker-compose logs -f

# 7. 初始化数据库（首次）
docker-compose exec backend alembic upgrade head
```

### 配置说明

#### 数据库配置

**SQLite（开发环境）**
```bash
DATABASE_URL=sqlite:///./data/livecalc.db
```

**PostgreSQL（生产环境）**
```bash
DATABASE_URL=postgresql://user:password@db:5432/livecalc
```

**MySQL（生产环境）**
```bash
DATABASE_URL=mysql+pymysql://user:password@db:3306/livecalc
```

#### 安全配置

```bash
# 生成安全的密钥（生产环境）
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

#### 地图服务配置（可选）

```bash
# 高德地图
AMAP_API_KEY=your-amap-key

# 百度地图
BAIDU_API_KEY=your-baidu-key

# 腾讯地图
TENCENT_API_KEY=your-tencent-key

# 天地图
TIANDITU_API_KEY=your-tianditu-key
```

### Docker Compose 服务说明

```yaml
services:
  # 后端 API 服务
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/livecalc
    depends_on:
      - db

  # 前端 Web 服务
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  # 数据库服务
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=livecalc
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # 任务队列（可选）
  celery:
    build: ./backend
    command: celery -A app.core.celery worker --loglevel=info
    depends_on:
      - backend
      - redis

  # Redis 缓存
  redis:
    image: redis:7-alpine
```

### 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 备份数据库
docker-compose exec db pg_dump -U livecalc livecalc > backup.sql

# 3. 停止服务
docker-compose down

# 4. 重新构建并启动
docker-compose up -d --build

# 5. 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 6. 清理旧镜像（可选）
docker image prune -f
```

### Docker 常用命令

```bash
# 查看运行中的容器
docker-compose ps

# 查看日志
docker-compose logs -f [service_name]

# 重启服务
docker-compose restart [service_name]

# 进入容器
docker-compose exec backend bash

# 停止所有服务
docker-compose down

# 停止并删除卷（危险操作）
docker-compose down -v
```

---

## 直接部署

### 后端部署

#### 1. 安装 Python 环境

```bash
# 安装 Python 3.11+
sudo apt-get install python3.11 python3.11-venv

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

#### 2. 安装依赖

```bash
cd backend

# 使用 requirements.txt
pip install -r requirements.txt

# 或使用 Poetry
pip install poetry
poetry install
```

#### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

#### 4. 初始化数据库

```bash
# 执行数据库迁移
alembic upgrade head
```

#### 5. 启动服务

**开发环境：**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生产环境（使用 Gunicorn）：**
```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

**使用 Systemd 服务（推荐）：**

创建 `/etc/systemd/system/livecalc.service`：

```ini
[Unit]
Description=Live Calc Backend API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/live_calc/backend
Environment="PATH=/path/to/live_calc/backend/venv/bin"
ExecStart=/path/to/live_calc/backend/venv/bin/gunicorn \
    app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable livecalc
sudo systemctl start livecalc
sudo systemctl status livecalc
```

### 前端部署

#### 1. 安装 Node.js

```bash
# 使用 NodeSource 仓库
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证安装
node --version
npm --version
```

#### 2. 安装依赖并构建

```bash
cd frontend

# 安装依赖
npm install

# 配置生产环境变量
echo "VITE_API_URL=https://your-domain.com/api/v1" > .env.production

# 构建生产版本
npm run build
```

#### 3. 使用 Nginx 托管

```bash
# 安装 Nginx
sudo apt-get install nginx

# 复制构建产物
sudo cp -r dist/* /var/www/livecalc/
```

---

## Nginx 配置

### 完整配置示例

创建 `/etc/nginx/sites-available/livecalc`：

```nginx
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 日志
    access_log /var/log/nginx/livecalc-access.log;
    error_log /var/log/nginx/livecalc-error.log;

    # 前端静态文件
    location / {
        root /var/www/livecalc;
        try_files $uri $uri/ /index.html;

        # 缓存控制
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
    }

    # WebSocket 支持（如需要）
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/livecalc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## SSL 配置

### 使用 Let's Encrypt（免费 SSL）

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书（自动配置 Nginx）
sudo certbot --nginx -d your-domain.com

# 手动获取证书
sudo certbot certonly --nginx -d your-domain.com

# 测试续期
sudo certbot renew --dry-run
```

### 自动续期

Certbot 会自动设置续期任务，验证：

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

### 付费 SSL 证书

如果使用付费证书（如 Cloudflare、阿里云等）：

1. 下载证书文件
2. 上传到服务器 `/etc/ssl/private/`
3. 更新 Nginx 配置中的证书路径
4. 重载 Nginx：`sudo systemctl reload nginx`

---

## 备份与恢复

### 数据库备份

**PostgreSQL：**
```bash
# 备份
docker-compose exec db pg_dump -U livecalc livecalc > backup_$(date +%Y%m%d).sql

# 只备份结构
docker-compose exec db pg_dump -U livecalc --schema-only livecalc > schema.sql

# 备份并压缩
docker-compose exec db pg_dump -U livecalc livecalc | gzip > backup_$(date +%Y%m%d).sql.gz
```

**SQLite：**
```bash
# 备份
cp backend/data/livecalc.db backup_$(date +%Y%m%d).db

# 使用 SQLite 命令
sqlite3 backend/data/livecalc.db ".backup backup.db"
```

### 自动备份脚本

创建 `/home/user/backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/home/user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T db pg_dump -U livecalc livecalc | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 删除 30 天前的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

添加到 crontab（每天凌晨 2 点备份）：
```bash
crontab -e
# 添加：0 2 * * * /home/user/backup.sh >> /home/user/backup.log 2>&1
```

### 数据恢复

**PostgreSQL：**
```bash
# 恢复
docker-compose exec -T db psql -U livecalc livecalc < backup.sql

# 恢复压缩备份
gunzip < backup.sql.gz | docker-compose exec -T db psql -U livecalc livecalc
```

**SQLite：**
```bash
# 停止服务
docker-compose stop backend

# 恢复
cp backup.db backend/data/livecalc.db

# 重启服务
docker-compose start backend
```

---

## 监控与日志

### 日志管理

```bash
# 查看后端日志
docker-compose logs -f backend

# 查看最近 100 行日志
docker-compose logs --tail=100 backend

# 查看所有服务日志
docker-compose logs

# 清理日志（Docker）
docker system prune -a
```

### 监控工具

**使用 Docker Stats：**
```bash
docker stats
```

**使用 htop：**
```bash
sudo apt-get install htop
htop
```

**系统监控（可选）：**
- Prometheus + Grafana
- Datadog
- New Relic

### 性能优化

1. **数据库优化**
   - 添加适当索引
   - 定期清理旧数据
   - 使用连接池

2. **后端优化**
   - 启用缓存（Redis）
   - 使用异步任务处理
   - 调整 worker 数量

3. **前端优化**
   - 启用 CDN
   - 配置缓存策略
   - 压缩静态资源

---

## 常见问题

### 问题 1: 数据库连接失败

**症状：** 后端无法连接数据库

**解决方案：**
```bash
# 检查数据库是否运行
docker-compose ps db

# 检查数据库日志
docker-compose logs db

# 检查网络连接
docker-compose exec backend ping db
```

### 问题 2: 静态文件 404

**症状：** 前端页面显示 404

**解决方案：**
```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查文件权限
sudo chown -R www-data:www-data /var/www/livecalc

# 检查构建产物
ls -la /var/www/livecalc
```

### 问题 3: 迁移失败

**症状：** `alembic upgrade head` 失败

**解决方案：**
```bash
# 检查当前版本
docker-compose exec backend alembic current

# 查看迁移历史
docker-compose exec backend alembic history

# 强制回滚到指定版本
docker-compose exec backend alembic downgrade base
```

### 问题 4: 权限错误

**症状：** `Permission denied` 错误

**解决方案：**
```bash
# 调整文件权限
sudo chown -R $USER:$USER .
sudo chmod -R 755 .

# Docker 容器权限
sudo usermod -aG docker $USER
```

### 问题 5: 内存不足

**症状：** OOM (Out of Memory) 错误

**解决方案：**
```bash
# 限制 Docker 内存
# 编辑 /etc/docker/daemon.json
{
  "default-runtime": "runc",
  "default-ulimits": {
    "memlock": {
      "Name": "memlock",
      "Hard": -1,
      "Soft": -1
    }
  }
}

# 重启 Docker
sudo systemctl restart docker
```

---

## 安全建议

1. **定期更新依赖**
   ```bash
   pip list --outdated
   npm outdated
   ```

2. **使用强密码和密钥**
   ```bash
   # 生成随机密钥
   openssl rand -hex 32
   ```

3. **启用防火墙**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **配置 fail2ban 防止暴力破解**
   ```bash
   sudo apt-get install fail2ban
   ```

5. **定期备份数据**
   - 设置自动备份
   - 测试恢复流程
   - 保留多个备份版本

---

## 获取帮助

如果遇到问题，请：

1. 查看 [常见问题](#常见问题) 部分
2. 检查日志文件
3. 在 GitHub 提交 Issue
4. 联系技术支持

---

**文档版本**: 1.0
**最后更新**: 2026-02-25
