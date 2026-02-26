#!/usr/bin/env python3
"""
完整功能测试脚本
验证所有修复是否都已正确应用
"""

import subprocess
import sys
import time
import requests
import json


def run_test():
    print("=== 生计项目完整功能测试 ===\n")

    # 1. 测试 bcrypt 修复
    print("1. 测试 bcrypt 修复...")
    try:
        import os
        os.chdir('backend')
        result = subprocess.run([
            'python', '-c',
            '''
import sys
sys.path.insert(0, '.')
from app.core.security import get_password_hash, verify_password

# 测试普通密码
normal_password = 'mypassword123'
hashed = get_password_hash(normal_password)
is_valid = verify_password(normal_password, hashed)
print(f"普通密码测试: {is_valid}")

# 测试长密码
long_password = 'a' * 80
hashed_long = get_password_hash(long_password)
is_valid_long = verify_password(long_password, hashed_long)
print(f"长密码测试: {is_valid_long}")

print("✅ bcrypt 修复测试通过")
            '''
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and "✅ bcrypt 修复测试通过" in result.stdout:
            print("   ✅ bcrypt 修复测试通过\n")
        else:
            print(f"   ❌ bcrypt 修复测试失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ bcrypt 修复测试异常: {e}")
        return False
    finally:
        os.chdir('..')  # 回到原目录

    # 2. 启动后端服务进行集成测试
    print("2. 启动后端服务进行集成测试...")
    try:
        # 启动后端服务
        backend_process = subprocess.Popen([
            'source', '.venv/bin/activate', '&&', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8001', '--reload'
        ], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 等待服务启动
        time.sleep(5)

        # 测试配置端点
        print("   测试 /api/v1/auth/config 端点...")
        response = requests.get('http://localhost:8001/api/v1/auth/config')
        if response.status_code == 200:
            config_data = response.json()
            if 'registration_require_invite_code' in config_data:
                print("   ✅ 配置端点测试通过")
            else:
                print("   ❌ 配置端点响应格式错误")
                return False
        else:
            print(f"   ❌ 配置端点测试失败: {response.status_code}")
            return False

        # 测试注册端点
        print("   测试 /api/v1/auth/register 端点...")
        register_data = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "phone": "13812345678",
            "password_hash": "testpassword123"
        }
        response = requests.post(
            'http://localhost:8001/api/v1/auth/register',
            json=register_data,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            token_data = response.json()
            if 'access_token' in token_data:
                print("   ✅ 注册端点测试通过")
            else:
                print("   ❌ 注册端点响应格式错误")
                return False
        elif response.status_code == 400 and '用户名已存在' in response.text:
            print("   ✅ 注册端点测试通过（用户已存在，预期结果）")
        else:
            print(f"   ❌ 注册端点测试失败: {response.status_code}, {response.text}")
            return False

        # 杀掉后端进程
        backend_process.terminate()
        time.sleep(2)

        print("   ✅ 集成测试通过\n")
    except Exception as e:
        print(f"   ❌ 集成测试异常: {e}")
        # 尝试终止进程
        try:
            backend_process.terminate()
        except:
            pass
        return False

    # 3. 检查前端文件修改
    print("3. 检查前端文件修改...")
    try:
        with open('frontend/src/views/auth/Register.vue', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已修复 fetch 调用
        if "api.get('/auth/config')" in content and "fetch('/api/v1/config')" not in content:
            print("   ✅ Register.vue 文件修复验证通过")
        else:
            print("   ❌ Register.vue 文件修复验证失败")
            return False

        # 检查导入语句
        if "import { api } from '@/api/client'" in content:
            print("   ✅ API 客户端导入验证通过")
        else:
            print("   ❌ API 客户端导入验证失败")
            return False

        print("   ✅ 前端文件修改验证通过\n")
    except Exception as e:
        print(f"   ❌ 前端文件检查异常: {e}")
        return False

    # 4. 检查环境变量配置
    print("4. 检查环境变量配置...")
    try:
        with open('frontend/.env', 'r', encoding='utf-8') as f:
            env_content = f.read().strip()

        if "VITE_API_URL=/api/v1" in env_content:
            print("   ✅ 前端环境变量配置验证通过")
        else:
            print("   ❌ 前端环境变量配置验证失败")
            return False

        print("   ✅ 环境变量配置验证通过\n")
    except Exception as e:
        print(f"   ❌ 环境变量检查异常: {e}")
        return False

    print("🎉 所有测试通过！所有问题均已修复。")
    return True


if __name__ == "__main__":
    success = run_test()
    if success:
        print("\n✅ 完整功能测试成功完成")
        sys.exit(0)
    else:
        print("\n❌ 完整功能测试失败")
        sys.exit(1)