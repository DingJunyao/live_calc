# backend/tests/services/test_usda_importer.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.usda import UsdaFood, UsdaFoodNutrient
from app.services.usda.importer import UsdaImporter


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_import_inserts_food_and_nutrients(db):
    entries = [{
        "fdc_id": 1, "data_type": "foundation", "description": "Apple, raw",
        "publication_date": "2024-04",
        "nutrients": [
            {"nutrient_no": "208", "name": "Energy", "name_zh": "能量", "amount": 52.0, "unit_name": "kcal"},
        ],
    }]
    result = UsdaImporter(db).import_entries(entries)
    assert result["inserted"] == 1
    assert db.query(UsdaFood).count() == 1
    assert db.query(UsdaFoodNutrient).count() == 1


def test_import_upsert_updates_existing(db):
    importer = UsdaImporter(db)
    entries_v1 = [{"fdc_id": 1, "data_type": "foundation", "description": "Apple, raw",
                   "nutrients": [{"name": "Energy", "amount": 52, "unit_name": "kcal"}]}]
    importer.import_entries(entries_v1)
    entries_v2 = [{"fdc_id": 1, "data_type": "foundation", "description": "Apple, raw",
                   "nutrients": [{"name": "Energy", "amount": 60, "unit_name": "kcal"},
                                 {"name": "Protein", "amount": 0.3, "unit_name": "g"}]}]
    result = importer.import_entries(entries_v2)
    assert result["updated"] == 1
    food = db.query(UsdaFood).filter(UsdaFood.fdc_id == 1).one()
    assert db.query(UsdaFoodNutrient).filter(UsdaFoodNutrient.fdc_id == 1).count() == 2
    # 更新时重置翻译状态（描述可能变了）
    assert food.translate_status == "pending"
