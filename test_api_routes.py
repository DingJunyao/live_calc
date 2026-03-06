import os
import sys

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.main import app
from starlette.testclient import TestClient

# 创建测试客户端
client = TestClient(app)

print("测试API路由...")

# 尝试访问商家API（这个调用将失败，因为没有认证，但我们能看到路由是否存在）
response = client.get("/api/v1/merchants/")
print(f"GET /api/v1/merchants/: {response.status_code} - {response.text}")

# 检查其他已知的API端点，确认测试客户端工作正常
try:
    response_auth_config = client.get("/api/v1/auth/config")
    print(f"GET /api/v1/auth/config: {response_auth_config.status_code} - {response_auth_config.text[:100]}")
except Exception as e:
    print(f"GET /api/v1/auth/config error: {e}")

# 尝试不带前缀的路由
try:
    response_root = client.get("/")
    print(f"GET /: {response_root.status_code} - {response_root.text[:100]}")
except Exception as e:
    print(f"GET / error: {e}")