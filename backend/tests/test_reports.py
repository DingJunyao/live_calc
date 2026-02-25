import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_expense():
    """测试创建费用记录"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"}
    )
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/reports/expenses/",
        json={
            "type": "water",
            "amount": 15.5,
            "unit": "立方米",
            "date": "2024-01-15"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_get_expense_report():
    """测试获取支出报告"""
    response = client.get("/api/v1/reports/expense?start_date=2024-01-01&end_date=2024-01-31")
    assert response.status_code in [200, 401]


def test_get_price_trend():
    """测试获取价格趋势"""
    response = client.get("/api/v1/reports/price-trend?product_name=鸡蛋")
    assert response.status_code in [200, 401]
