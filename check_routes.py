#!/usr/bin/env python3
"""
检查FastAPI应用路由的调试脚本
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 更改工作目录到backend目录
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

from app.main import app

def check_routes():
    print("检查FastAPI应用路由...")
    print(f"总路由数量: {len(app.routes)}")

    print("\n所有注册的路由:")
    for i, route in enumerate(app.routes):
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = getattr(route, 'methods', [])
            if isinstance(methods, set):
                methods = list(methods)
            print(f"{i+1:2d}. {', '.join(sorted(methods))} {route.path} (name: {getattr(route, 'name', 'N/A')})")
        else:
            print(f"{i+1:2d}. {route.__class__.__name__}: {getattr(route, 'path', 'N/A')}")

    # 特别检查商家相关的路由
    print("\n商家相关路由:")
    for i, route in enumerate(app.routes):
        if hasattr(route, 'path') and 'merchant' in route.path.lower():
            methods = getattr(route, 'methods', [])
            if isinstance(methods, set):
                methods = list(methods)
            print(f"  - {', '.join(sorted(methods))} {route.path}")

if __name__ == "__main__":
    check_routes()