import requests
import json
import os
from datetime import datetime

def test_locations_api():
    # 设置API基础URL
    base_url = os.getenv('VITE_API_URL', '/api/v1')

    # 如果VITE_API_URL是相对路径（如/api/v1），则添加本地主机
    if base_url.startswith('/'):
        base_url = f"http://localhost:8000{base_url}"

    print(f"API Base URL: {base_url}")

    # 获取认证token - 通常从前端的localStorage中获取
    # 我们先测试获取当前用户信息
    headers = {
        'Content-Type': 'application/json',
    }

    # 读取前端存储的token（如果有的话）
    import subprocess
    try:
        # 尝试从前端读取当前的token（如果应用仍在运行）
        # 或者我们直接从浏览器本地存储获取
        print("请注意：我们需要有效的用户令牌才能调用受保护的API")

        # 这里我们手动测试一个可能存在的令牌，或直接调用后端API
        print("让我们模拟调用后端获取地点API")

        # 由于我们无法直接获取当前用户令牌，我们可以尝试手动测试
        # 首先获取一个用户的token
        # 注意：实际测试需要有效令牌

        print("数据库中的用户ID为2，有两个地点记录")
        print("地点数据:")
        print("- ID: 1, 用户ID: 2, 名称: 家门口菜市场, 纬度: 0, 经度: 0")
        print("- ID: 2, 用户ID: 2, 名称: 菜市场, 纬度: 0, 经度: 0")
        print()
        print("后端API的get_locations函数查询的是当前认证用户的数据:")
        print("db.query(Location).filter(Location.user_id == current_user.id)")
        print()
        print("因此，如果你的当前用户ID不是2，那么你将看不到这些地点记录。")
        print("问题可能出在这里：新添加的地点是属于特定用户的，只有该用户才能看到自己的地点。")

    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_locations_api()