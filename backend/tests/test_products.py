import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_product_record():
    """测试创建商品记录"""
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
    """测试获取商品记录列表"""
    response = client.get("/api/v1/products/")
    # 需要登录
    assert response.status_code in [200, 401]


def test_get_product_history():
    """测试获取商品历史价格"""
    # 先登录
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    # 获取历史
    response = client.get(
        "/api/v1/products/history/鸡蛋",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_name"] == "鸡蛋"
