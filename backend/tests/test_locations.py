import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_location():
    """测试创建地点"""
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


def test_get_locations():
    """测试获取地点列表"""
    response = client.get("/api/v1/locations/")
    # 需要登录
    assert response.status_code in [200, 401]


def test_create_favorite_location():
    """测试创建常用位置"""
    # 先登录
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    # 创建常用位置
    response = client.post(
        "/api/v1/locations/favorites/",
        json={
            "name": "家",
            "type": "home",
            "latitude": 39.9,
            "longitude": 116.4
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "家"
