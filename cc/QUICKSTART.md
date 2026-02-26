
## 🚀 快速启动指南

### Docker 部署（推荐）
```bash
docker-compose up -d
```

访问: http://localhost

### 本地开发

#### 后端
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 前端
```bash
cd frontend
npm run dev
```

访问: http://localhost:5173（或 Vite 显示的其他端口）

### 常见问题

1. **前端构建失败** - 确保有 index.html
2. **端口被占用** - Vite 会自动选择其他端口
3. **API 404** - 确保后端正在运行
4. **CORS 错误** - 检查后端 CORS 配置

