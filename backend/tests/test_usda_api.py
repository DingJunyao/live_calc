# backend/tests/test_usda_api.py
"""USDA 搜索/详情 API 测试。

数据库与鉴权 override 由 `tests/conftest.py` 统一提供（共享内存 SQLite +
FakeUser），通过 `clean_usda_tables` fixture 按测试安装/恢复，避免与
`test_usda_admin_api.py` 在模块级互相覆盖 dependency_overrides。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.usda import UsdaFood, UsdaFoodNutrient
from app.services.usda.index_manager import build_usda_index
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData

from conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture()
def db_with_data(clean_usda_tables):
    db = TestingSessionLocal()
    db.add(UsdaFood(
        fdc_id=100,
        data_type="foundation",
        description="Apple, raw",
        description_zh="苹果（生）",
    ))
    db.add(UsdaFoodNutrient(
        fdc_id=100,
        name="Energy",
        name_zh="能量",
        amount=52,
        unit_name="kcal",
    ))
    db.commit()
    # 刷新索引指向内存数据，确保 search 能命中
    build_usda_index(db)
    yield db
    db.query(UsdaFoodNutrient).delete()
    db.query(UsdaFood).delete()
    db.commit()
    db.close()


def test_search(db_with_data):
    r = client.get("/api/v1/usda/search", params={"q": "苹果"})
    assert r.status_code == 200
    data = r.json()
    assert any(item["fdc_id"] == 100 for item in data)


def test_detail(db_with_data):
    r = client.get("/api/v1/usda/100")
    assert r.status_code == 200
    d = r.json()
    assert d["fdc_id"] == 100
    assert len(d["nutrients"]) == 1
    assert d["nutrients"][0]["name_zh"] == "能量"


# ---------- 匹配写入端点 ----------


def test_match_ingredient_endpoint(db_with_data):
    # db_with_data 已有 fdc_id=100 的 usda_food + Energy nutrient
    db = TestingSessionLocal()
    ing = Ingredient(name="苹果", is_active=True)
    db.add(ing); db.commit(); db.flush()
    ing_id = ing.id
    db.close()
    r = client.post(f"/api/v1/usda/match/ingredient/{ing_id}", json={"fdc_id": 100})
    assert r.status_code == 200
    assert r.json()["fdc_id"] == 100
    # 验证写入
    db = TestingSessionLocal()
    nd = db.query(NutritionData).filter(NutritionData.ingredient_id == ing_id).first()
    assert nd is not None
    assert nd.source == "usda_manual_match"
    db.query(NutritionData).filter(NutritionData.ingredient_id == ing_id).delete()
    db.query(Ingredient).filter(Ingredient.id == ing_id).delete()
    db.commit(); db.close()


def test_match_ingredient_not_found(db_with_data):
    r = client.post("/api/v1/usda/match/ingredient/999999", json={"fdc_id": 100})
    assert r.status_code == 404


def test_match_fdc_not_found(db_with_data):
    db = TestingSessionLocal()
    ing = Ingredient(name="测试原料", is_active=True)
    db.add(ing); db.commit(); db.flush()
    ing_id = ing.id
    db.close()
    r = client.post(f"/api/v1/usda/match/ingredient/{ing_id}", json={"fdc_id": 999999})
    assert r.status_code == 404
    # 清理
    db = TestingSessionLocal()
    db.query(Ingredient).filter(Ingredient.id == ing_id).delete()
    db.commit(); db.close()


# ---------- 预览端点 ----------


def test_preview_nutrition_endpoint(db_with_data):
    """GET /api/v1/usda/preview-nutrition?fdc_id=... 返回三层结构。"""
    db = TestingSessionLocal()
    db.add(UsdaFood(
        fdc_id=770501,
        data_type="foundation",
        description="Preview Food",
    ))
    db.add(UsdaFoodNutrient(
        fdc_id=770501,
        name="Energy",
        name_zh="能量",
        amount=100.0,
        unit_name="kcal",
    ))
    db.commit()
    db.close()

    resp = client.get("/api/v1/usda/preview-nutrition", params={"fdc_id": 770501})
    assert resp.status_code == 200
    body = resp.json()
    assert "core_nutrients" in body
    assert "能量" in body["core_nutrients"]


def test_preview_nutrition_not_found(db_with_data):
    resp = client.get("/api/v1/usda/preview-nutrition", params={"fdc_id": 770599})
    assert resp.status_code == 404
