"""Test image scan endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.image_tracking import ImageTracking

BASE = "/api/v1/admin"
client = TestClient(app)


def test_scan_endpoint(db_session, as_admin):
    """Test that scan endpoint works and returns stats."""
    db_session.add(ImageTracking(key="recipes/test_scan.jpg", ref_count=0))
    db_session.commit()

    resp = client.post(f"{BASE}/images/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert "stats" in data
    assert data["message"] == "扫描完成"


def test_unused_endpoint(db_session, as_admin):
    """Test that unused endpoint returns grouped data."""
    db_session.add(ImageTracking(key="recipes/test_unused.jpg", ref_count=0))
    db_session.commit()

    client.post(f"{BASE}/images/scan")

    resp = client.get(f"{BASE}/images/unused")
    assert resp.status_code == 200
    data = resp.json()
    assert "stats" in data
    assert "groups" in data
