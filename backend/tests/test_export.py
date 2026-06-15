import io
import zipfile
import json

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _extract_zip(response):
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    return zf


def test_export_full_returns_valid_zip():
    token = _login_token()
    resp = client.get(
        "/api/v1/export/data?scope=full",
        headers={"Authorization": f"Bearer {token}"},
    )
    zf = _extract_zip(resp)
    names = zf.namelist()
    assert "manifest.json" in names
    assert "ingredients.json" in names
    assert "units.json" in names
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["scope"] == "full"
    assert "counts" in manifest


def test_export_mine_returns_valid_zip():
    token = _login_token()
    resp = client.get(
        "/api/v1/export/data?scope=mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    zf = _extract_zip(resp)
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["scope"] == "mine"
    recipe_files = [n for n in zf.namelist() if n.startswith("recipes/") and n.endswith(".json")]
    assert len(recipe_files) == manifest["counts"].get("recipes", 0)


def test_export_requires_auth():
    resp = client.get("/api/v1/export/data?scope=full")
    assert resp.status_code in (401, 403)
