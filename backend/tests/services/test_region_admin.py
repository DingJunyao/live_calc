from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def test_seed_status_requires_admin(as_non_admin):
    """非管理员访问 seed-status 应被拒（403）。"""
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/v1/admin/regions/seed-status")
    assert r.status_code == 403


def test_seed_status_returns_counts_and_needed(as_admin):
    """GET /admin/regions/seed-status 返各级 count + needed，管理员鉴权。"""
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/v1/admin/regions/seed-status")
    assert r.status_code == 200
    body = r.json()
    assert "counts" in body and "needed" in body and "total" in body
    assert set(body["counts"].keys()) == {"0", "1", "2", "3"}


def test_seed_endpoint_calls_upsert(as_admin):
    """POST /admin/regions/seed 调 upsert_administrative_regions，返 created/skipped/errors。"""
    from app.main import app
    from app.api import regions
    with patch.object(regions, "upsert_administrative_regions", return_value={"created": 10, "skipped": 2, "errors": 0}):
        client = TestClient(app)
        r = client.post("/api/v1/admin/regions/seed")
    assert r.status_code == 200
    assert r.json() == {"created": 10, "skipped": 2, "errors": 0}
