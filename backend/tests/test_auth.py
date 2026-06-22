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


# ===== token 失效测试（重置密码作废旧 token）=====

def _admin_token(username="token_admin"):
    """注册指定用户并提升为管理员，返回其 access_token。重复调用幂等。"""
    from app.core.database import SessionLocal
    from app.models.user import User
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@test.com",
              "password_hash": "admin_hash"},
    )
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if u and not u.is_admin:
            u.is_admin = True
            db.commit()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password_hash": "admin_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_reset_password_invalidates_old_tokens():
    """重置密码后，旧 access 与 refresh token 立即失效，新密码可登录。"""
    admin_headers = {"Authorization": f"Bearer {_admin_token()}"}

    # 建普通用户并登录拿 token
    client.post(
        "/api/v1/auth/register",
        json={"username": "reset_target", "email": "reset_target@test.com",
              "password_hash": "old_hash"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "reset_target", "password_hash": "old_hash"},
    ).json()
    target_access = login["access_token"]
    target_refresh = login["refresh_token"]
    target_headers = {"Authorization": f"Bearer {target_access}"}

    # 取 target id
    target_id = client.get("/api/v1/auth/me", headers=target_headers).json()["id"]

    # 重置前：旧 token 可用
    assert client.get("/api/v1/auth/me", headers=target_headers).status_code == 200

    # 管理员重置 target 密码
    resp = client.put(
        f"/api/v1/auth/users/{target_id}",
        json={"password_hash": "new_hash"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # 重置后：旧 access token 失效
    assert client.get("/api/v1/auth/me", headers=target_headers).status_code == 401

    # 重置后：旧 refresh token 也失效
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": target_refresh},
    ).status_code == 401

    # 重置后：用新密码能登录并拿到有效 token
    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "reset_target", "password_hash": "new_hash"},
    )
    assert new_login.status_code == 200
    new_access = new_login.json()["access_token"]
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    ).status_code == 200


def test_update_other_fields_keeps_token_valid():
    """仅修改非密码字段时，token 保持有效。"""
    admin_headers = {"Authorization": f"Bearer {_admin_token('keep_admin')}"}

    client.post(
        "/api/v1/auth/register",
        json={"username": "keep_target", "email": "keep_target@test.com",
              "password_hash": "pw_hash"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "keep_target", "password_hash": "pw_hash"},
    ).json()
    target_headers = {"Authorization": f"Bearer {login['access_token']}"}
    target_id = client.get("/api/v1/auth/me", headers=target_headers).json()["id"]

    # 仅改邮箱，不带 password_hash
    resp = client.put(
        f"/api/v1/auth/users/{target_id}",
        json={"email": "keep_target_new@test.com"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # token 仍有效
    assert client.get("/api/v1/auth/me", headers=target_headers).status_code == 200
