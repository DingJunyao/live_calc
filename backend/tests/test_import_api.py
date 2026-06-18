"""测试导入 API。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _setup_users():
    """确保测试用户存在。"""
    # Register admin if not exists
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin",
            "email": "admin@test.com",
            "password_hash": "admin_password_hash",
        },
    )
    if resp.status_code == 200:
        # Promote to admin (first user already exists, so new user is not admin by default)
        from app.core.database import SessionLocal
        from app.models.user import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "admin").first()
            if user:
                user.is_admin = True
                db.commit()
        finally:
            db.close()

    # Register testuser if not exists (will 400 if already exists)
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "testuser@test.com",
            "password_hash": "test_password_hash",
        },
    )


_setup_users()


def _admin_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password_hash": "admin_password_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _user_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_upload_requires_auth():
    """未登录用户无法上传导入。"""
    resp = client.post("/api/v1/import/data/upload")
    assert resp.status_code in (401, 403)


def test_repo_import_admin_only():
    """非管理员无法触发仓库导入。"""
    token = _user_token()
    resp = client.post(
        "/api/v1/import/data/import-from-repo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_local_import_admin_only():
    """非管理员无法触发本地目录导入。"""
    token = _user_token()
    resp = client.post(
        "/api/v1/import/data/import-from-local?local_path=/tmp",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_upload_rejects_non_zip():
    """非 ZIP 文件应被拒绝。"""
    token = _admin_token()
    resp = client.post(
        "/api/v1/import/data/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert "ZIP" in resp.text or "zip" in resp.text
