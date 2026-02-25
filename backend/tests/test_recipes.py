import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_recipe():
    """测试创建菜谱"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/recipes/",
        json={
            "name": "番茄炒蛋",
            "source": "custom",
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


def test_get_recipes():
    """测试获取菜谱列表"""
    response = client.get("/api/v1/recipes/")
    assert response.status_code in [200, 401]


def test_get_recipe_cost():
    """测试获取菜谱成本"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    response = client.get(
        "/api/v1/recipes/1/cost",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [200, 404]
