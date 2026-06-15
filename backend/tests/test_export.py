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


def test_export_howto_cook_compatibility():
    """导出的菜谱/食材/营养/单位字段符合 HowToCook 结构。"""
    token = _login_token()
    resp = client.get(
        "/api/v1/export/data?scope=full",
        headers={"Authorization": f"Bearer {token}"},
    )
    zf = _extract_zip(resp)

    # 单位：数组，每项含 name + aliases
    units = json.loads(zf.read("units.json"))
    assert isinstance(units, list)
    if units:
        assert "name" in units[0] and "aliases" in units[0]

    # 食材：dict，value 含 HowToCook 字段
    ingredients = json.loads(zf.read("ingredients.json"))
    assert isinstance(ingredients, dict)
    if ingredients:
        sample = next(iter(ingredients.values()))
        for k in ("name", "aliases", "category", "usda_id", "usda_match_status"):
            assert k in sample

    # 营养：数组，元素含 usda_id + nutrients[]
    nutritions = json.loads(zf.read("nutritions.json"))
    assert isinstance(nutritions, list)
    if nutritions:
        assert "usda_id" in nutritions[0]
        assert isinstance(nutritions[0].get("nutrients"), list)

    # 菜谱文件：含 HowToCook 必需字段
    recipe_files = [n for n in zf.namelist() if n.startswith("recipes/") and n.endswith(".json")]
    if recipe_files:
        r = json.loads(zf.read(recipe_files[0]))
        for k in ("name", "ingredients", "steps"):
            assert k in r
        if r["ingredients"]:
            for k in ("ingredient_name", "quantity", "unit"):
                assert k in r["ingredients"][0]
