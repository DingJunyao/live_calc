import os
import sys
import hashlib
import sqlite3

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 从后端应用导入依赖
os.chdir('backend')

from app.main import app
from app.core.security import create_access_token
from app.models.user import User
from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from starlette.testclient import TestClient
import json

# 创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # 尝试获取第一个用户
    user = db.query(User).first()
    
    if user:
        print(f"Found user: {user.username}, ID: {user.id}, is_admin: {user.is_admin}")
        
        # 创建测试客户端
        client = TestClient(app)
        
        # 使用用户名和预设密码尝试登录（如果有的话）
        # 注意：这里使用了一个常见测试密码，实际应用中不应硬编码密码
        login_data = {
            "username": user.username,
            "password": "Bill123456"  # 假设这是测试密码
        }
        
        # 由于前端会对密码进行SHA256处理，我们也需要这样做
        sha256_password = hashlib.sha256("Bill123456".encode()).hexdigest()
        login_data["password"] = sha256_password
        
        print("Attempting to get auth token...")
        login_response = client.post("/api/v1/auth/login", json=login_data)
        print(f"Login response: {login_response.status_code}")
        print(f"Login response text: {login_response.text}")
        
        # 如果登录失败，尝试使用测试客户端直接创建令牌
        if login_response.status_code != 200:
            print("\nTrying direct token creation...")
            # 直接创建访问令牌
            token_data = {"sub": str(user.id), "username": user.username}
            access_token = create_access_token(data=token_data)
            
            print(f"Created token for user {user.username}")
            
            # 使用令牌访问商家API
            headers = {"Authorization": f"Bearer {access_token}"}
            merchants_response = client.get("/api/v1/merchants/", headers=headers)
            print(f"Merchants API response: {merchants_response.status_code}")
            print(f"Merchants API response text: {merchants_response.text}")
        else:
            # 如果登录成功，提取令牌并访问商家API
            login_result = login_response.json()
            access_token = login_result.get('access_token')
            
            if access_token:
                headers = {"Authorization": f"Bearer {access_token}"}
                merchants_response = client.get("/api/v1/merchants/", headers=headers)
                print(f"Merchants API response: {merchants_response.status_code}")
                print(f"Merchants API response text: {merchants_response.text}")
            else:
                print("No access token in login response")
                
finally:
    db.close()
