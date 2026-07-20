"""Storage configuration management API tests."""
from unittest.mock import patch


def test_get_config_masks_secret(as_admin):
    """GET 返脱敏 secret + source。"""
    from app.services.storage.effective import StorageEffectiveConfig
    from starlette.testclient import TestClient
    from app.main import app

    fake = StorageEffectiveConfig(
        backend="s3", storage_base_url=None,
        s3_endpoint="https://x", s3_access_key="ak", s3_secret_key="secret-val",
        s3_bucket="b", s3_region="r", s3_url_style="path",
        sources={"backend": "db"},
    )
    with patch("app.api.storage_config.load_effective_storage_config", return_value=fake):
        client = TestClient(app)
        r = client.get("/api/v1/admin/storage-config")
    assert r.status_code == 200
    body = r.json()
    assert body["s3_secret_key"] == "***"
    assert body["has_secret"] is True
    assert body["sources"]["backend"] == "db"


def test_put_config_local_no_probe(as_admin):
    """PUT 切 local 不跑探针，直接写 DB。"""
    from starlette.testclient import TestClient
    from app.main import app

    with patch("app.api.storage_config._upsert_db") as upsert, \
         patch("app.api.storage_config.reset_storage"):
        client = TestClient(app)
        r = client.put("/api/v1/admin/storage-config", json={"backend": "local"})
    assert r.status_code == 200
    upsert.assert_called_once()


def test_test_endpoint_runs_probe(as_admin):
    """POST /test 用 body 配置探针，不落库。"""
    from starlette.testclient import TestClient
    from app.main import app

    with patch("app.api.storage_config._probe_s3", return_value=(True, None)) as p:
        client = TestClient(app)
        r = client.post("/api/v1/admin/storage-config/test", json={
            "backend": "s3", "s3_endpoint": "https://x", "s3_access_key": "ak",
            "s3_secret_key": "sk", "s3_bucket": "b", "s3_region": "", "s3_url_style": "path",
        })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    p.assert_called_once()


def test_migrate_returns_task_id(as_admin):
    """POST /migrate 建任务返 task_id。"""
    from starlette.testclient import TestClient
    from app.main import app

    with patch("app.services.storage.migrate.start_migrate_task", return_value=42) as sm:
        client = TestClient(app)
        r = client.post("/api/v1/admin/storage-config/migrate", json={"direction": "to_s3"})
    assert r.status_code == 200
    assert r.json()["task_id"] == 42
    sm.assert_called_once()
