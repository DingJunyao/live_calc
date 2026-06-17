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


def test_and_requires_all_tokens(db):
    """AND：空格分词每一项都须命中，缺一不可。"""
    idx = UsdaSearchIndex.build(db)
    # 1(鸡胸肉)同时含「鸡」「胸」→ 命中；2(鸡肝)只含「鸡」不含「胸」→ 淘汰
    results = idx.search("鸡 胸")
    assert [r["fdc_id"] for r in results] == [1]


def test_and_token_matches_either_zh_or_en(db):
    """每个分词只要中文名或英文名任一子串命中即算该项通过。"""
    idx = UsdaSearchIndex.build(db)
    # 单 token：中文/英文各自命中 1,2
    assert sorted(r["fdc_id"] for r in idx.search("鸡")) == [1, 2]
    assert sorted(r["fdc_id"] for r in idx.search("chicken")) == [1, 2]
    # 两 token：1,2 同时含 chicken(英) 与 鸡(中)，各项都命中 → 召回
    assert sorted(r["fdc_id"] for r in idx.search("chicken 鸡")) == [1, 2]
    # chicken 牛：1,2 含 chicken 不含牛；3 含牛不含 chicken → 全淘汰
    assert idx.search("chicken 牛") == []


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
