import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register():
    """测试用户注册"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "test_password_hash"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_register_duplicate_username():
    """测试重复用户名"""
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "duplicate",
            "email": "test1@example.com",
            "password_hash": "test_password_hash"
        }
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "duplicate",
            "email": "test2@example.com",
            "password_hash": "test_password_hash"
        }
    )
    assert response.status_code == 400
    assert "用户名已存在" in response.json()["detail"]


def test_login():
    """测试用户登录"""
    # 先注册
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser2",
            "email": "test2@example.com",
            "password_hash": "test_password_hash"
        }
    )

    # 再登录
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser2",
            "password_hash": "test_password_hash"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
