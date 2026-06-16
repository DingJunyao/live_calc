# backend/tests/services/test_usda_search.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.usda import UsdaFood
from app.services.usda.search import UsdaSearchIndex


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add_all([
        UsdaFood(fdc_id=1, data_type="foundation", description="Chicken, breast, raw", description_zh="鸡胸肉（生）"),
        UsdaFood(fdc_id=2, data_type="foundation", description="Chicken, liver, raw", description_zh="鸡肝（生）"),
        UsdaFood(fdc_id=3, data_type="foundation", description="Beef, raw", description_zh="牛肉（生）"),
    ])
    s.commit()
    yield s
    s.close()


def test_or_recall_any_token_hit(db):
    idx = UsdaSearchIndex.build(db)
    results = idx.search("鸡 胸")
    fdc_ids = [r["fdc_id"] for r in results]
    assert 1 in fdc_ids and 2 in fdc_ids
    assert results[0]["fdc_id"] == 1


def test_english_token_hit(db):
    idx = UsdaSearchIndex.build(db)
    results = idx.search("chicken")
    assert all(r["fdc_id"] in (1, 2) for r in results)


def test_exact_match_ranks_higher(db):
    idx = UsdaSearchIndex.build(db)
    results = idx.search("牛肉（生）")
    assert results[0]["fdc_id"] == 3


def test_no_match(db):
    idx = UsdaSearchIndex.build(db)
    assert idx.search("zzzzz") == []
