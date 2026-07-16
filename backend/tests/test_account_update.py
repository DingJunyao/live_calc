"""PUT /auth/me/account 端点测试。

用户名/邮箱用 uuid 后缀，避免与开发库历史测试数据撞名（注册唯一性）。
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _uniq(base: str) -> str:
    """生成唯一用户名后缀，避免跨次运行残留冲突。"""
    return f"{base}_{uuid.uuid4().hex[:8]}"


def _register_and_login(base: str = "acct", password_hash: str = "pw_hash"):
    """注册并登录，返回 (headers, user_id, username)。"""
    username = _uniq(base)
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@test.com",
              "password_hash": password_hash},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password_hash": password_hash},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    uid = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    return headers, uid, username


def test_change_username_success():
    headers, _, _ = _register_and_login("u1")
    new_name = _uniq("u1new")
    resp = client.put("/api/v1/auth/me/account",
                      json={"username": new_name}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == new_name
    # 不改密码时不含新 token
    assert body["access_token"] is None
    assert body["refresh_token"] is None


def test_change_username_duplicate():
    _, _, occupied_name = _register_and_login("u2")
    headers, _, _ = _register_and_login("u3")
    resp = client.put("/api/v1/auth/me/account",
                      json={"username": occupied_name}, headers=headers)
    assert resp.status_code == 400
    assert "占用" in resp.json()["detail"]


def test_change_email_duplicate():
    _, _, occupied_name = _register_and_login("u4")  # 占用 occupied_name@test.com
    headers, _, _ = _register_and_login("u5")
    resp = client.put("/api/v1/auth/me/account",
                      json={"email": f"{occupied_name}@test.com"}, headers=headers)
    assert resp.status_code == 400


def test_change_password_wrong_current():
    headers, _, _ = _register_and_login("u6", "old_hash")
    resp = client.put("/api/v1/auth/me/account",
                      json={"current_password": "wrong_hash",
                            "new_password": "new_hash"}, headers=headers)
    assert resp.status_code == 401
    assert "当前密码错误" in resp.json()["detail"]


def test_change_password_missing_current():
    headers, _, _ = _register_and_login("u7")
    resp = client.put("/api/v1/auth/me/account",
                      json={"new_password": "new_hash"}, headers=headers)
    assert resp.status_code == 400


def test_change_password_success_issues_new_token_and_invalidates_old():
    headers, _, username = _register_and_login("u8", "old_hash")

    resp = client.put("/api/v1/auth/me/account",
                      json={"current_password": "old_hash",
                            "new_password": "new_hash"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]

    # 旧 token 立即失效
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

    # 新 token 可用
    new_headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200

    # 新密码可登录
    assert client.post("/api/v1/auth/login",
                       json={"username": username, "password_hash": "new_hash"}
                       ).status_code == 200


def test_no_fields_no_password_change_keeps_token():
    headers, _, _ = _register_and_login("u9")
    # 只改用户名，不动密码 → 旧 token 仍有效
    resp = client.put("/api/v1/auth/me/account",
                      json={"username": _uniq("u9new")}, headers=headers)
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
