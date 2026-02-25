import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_nutrition():
    """测试搜索营养数据"""
    response = client.get("/api/v1/nutrition/search?query=鸡蛋")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_match_ingredient():
    """测试匹配食材"""
    response = client.post("/api/v1/nutrition/match?ingredient_name=有机鸡蛋")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)


def test_correct_mapping():
    """测试更正映射"""
    response = client.post(
        "/api/v1/nutrition/correct",
        json={
            "ingredient_name": "鸡蛋",
            "nutrition_id": 1
        }
    )
    assert response.status_code == 200
