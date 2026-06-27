"""P0 权限矩阵测试：共享数据写操作仅管理员，GET 至少需登录。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------- units.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_units_create_forbidden_for_non_admin():
    r = client.post("/api/v1/units/", json={"name": "测试单位", "abbreviation": "tst", "unit_type": "count"})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_admin")
def test_units_create_ok_for_admin():
    r = client.post("/api/v1/units/", json={"name": "测试单位A", "abbreviation": "tsta", "unit_type": "count"})
    assert r.status_code in (200, 201)


def test_units_list_requires_auth():
    # 无 override = 无 Authorization header → 401/403
    r = client.get("/api/v1/units/")
    assert r.status_code in (401, 403)


# ---------- nutrition.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_nutrition_ingredient_write_forbidden_for_non_admin():
    r = client.post("/api/v1/nutrition/ingredients/1/nutrition", json={"nutrients": {}})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_nutrition_correct_forbidden_for_non_admin():
    r = client.post("/api/v1/nutrition/correct", json={"ingredient_id": 1})
    assert r.status_code == 403


# ---------- usda.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_usda_match_ingredient_forbidden_for_non_admin():
    r = client.post("/api/v1/usda/match/ingredient/1", json={"fdc_id": 1})
    assert r.status_code == 403


# ---------- ingredient_hierarchy.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_create_forbidden_for_non_admin():
    r = client.post("/api/v1/ingredients/hierarchy",
                    json={"parent_id": 1, "child_id": 2, "relation_type": "contains"})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_merge_history_forbidden_for_non_admin():
    r = client.get("/api/v1/ingredients/merge-history")
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_update_forbidden_for_non_admin():
    r = client.put("/api/v1/ingredients/hierarchy/1", json={"strength": 50})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_delete_forbidden_for_non_admin():
    r = client.delete("/api/v1/ingredients/hierarchy/1")
    assert r.status_code == 403


# ---------- ingredient_extended.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_ingredient_hard_delete_forbidden_for_non_admin():
    r = client.delete("/api/v1/ingredients/1/hard")
    assert r.status_code == 403
