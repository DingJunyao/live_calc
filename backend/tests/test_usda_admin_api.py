# backend/tests/test_usda_admin_api.py
"""USDA 管理 API 测试。

数据库与鉴权 override 由 `tests/conftest.py` 统一提供（共享内存 SQLite +
FakeUser is_admin=True），通过 `clean_usda_tables` fixture 按测试安装/恢复，
避免与 `test_usda_api.py` 在模块级互相覆盖 dependency_overrides。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.usda import UsdaFood, UsdaFoodNutrient, TranslationConfig

from conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture()
def db_with_data(clean_usda_tables):
    db = TestingSessionLocal()
    db.add_all([
        UsdaFood(fdc_id=1, data_type="foundation", description="A", translate_status="done"),
        UsdaFood(fdc_id=2, data_type="foundation", description="B", translate_status="pending"),
    ])
    db.add(UsdaFoodNutrient(fdc_id=1, name="Energy", name_zh="能量", amount=1, unit_name="kcal"))
    db.add(UsdaFoodNutrient(fdc_id=1, name="Weird Nutrient", name_zh=None, amount=1, unit_name="g"))
    db.commit()
    yield db
    db.query(UsdaFoodNutrient).delete()
    db.query(UsdaFood).delete()
    db.commit()
    db.close()


def test_statistics(db_with_data):
    r = client.get("/api/v1/admin/usda/statistics")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2
    assert d["unmapped_nutrients"] >= 1


def test_unmapped_nutrients(db_with_data):
    r = client.get("/api/v1/admin/usda/unmapped-nutrients")
    assert r.status_code == 200
    d = r.json()
    assert "Weird Nutrient" in d["names"]


@pytest.fixture()
def clean_translation_config(clean_usda_tables):
    db = TestingSessionLocal()
    db.query(TranslationConfig).delete()
    db.commit()
    yield db
    db.query(TranslationConfig).delete()
    db.commit()
    db.close()


def test_translation_config_get_default(clean_translation_config):
    r = client.get("/api/v1/admin/translation-config")
    assert r.status_code == 200
    d = r.json()
    assert "ai" in d and "machine" in d
    assert "openai" in d["ai"]["providers"]
    assert "baidu" in d["machine"]["providers"]


def test_translation_config_put(clean_translation_config):
    new_cfg = {"ai": {"providers": {"openai": {"enabled": True, "base_url": "http://x/v1", "api_key": "k", "model": "m"}}}, "machine": {"providers": {}}}
    r = client.put("/api/v1/admin/translation-config", json={"config": new_cfg})
    assert r.status_code == 200
    # 再 GET 确认持久化
    r2 = client.get("/api/v1/admin/translation-config")
    assert r2.json()["ai"]["providers"]["openai"]["enabled"] is True


def test_translate_unknown_provider_400(clean_translation_config):
    # 不存在的 provider 名 → 400
    r = client.post("/api/v1/admin/usda/translate", json={"provider": "nonexistent_provider"})
    assert r.status_code == 400


def test_translation_config_test_unknown_provider_400(clean_translation_config):
    r = client.post("/api/v1/admin/translation-config/test", json={"provider": "nonexistent_provider"})
    assert r.status_code == 400
